import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from core.constants import RESTRICTED_USERNAMES, USERNAME_IS_PROHIBITED
from recipes.models import Ingredient, IngredientRecipe, Favorite, Recipe, ShoppingCart, Tag
from users.models import FgUser, Follow


User = get_user_model()


class FgUserCreateSerializer(UserCreateSerializer):
    """."""
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    class Meta(UserCreateSerializer.Meta):
        model = FgUser
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'password'
        )


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        # Если полученный объект строка, и эта строка 
        # начинается с 'data:image'...
        if isinstance(data, str) and data.startswith('data:image'):
            # ...начинаем декодировать изображение из base64.
            # Сначала нужно разделить строку на части.
            format, imgstr = data.split(';base64,')
            # И извлечь расширение файла.
            ext = format.split('/')[-1]
            # Затем декодировать сами данные и поместить результат в файл,
            # которому дать название по шаблону.
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class FgUserSerializer(UserSerializer):
    """Сериализатор пользователя."""

    is_subscribed = serializers.SerializerMethodField()
    # recipes = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = FgUser
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email',
            'is_subscribed', 'avatar',
            # 'recipes'
        )

    def get_is_subscribed(self, obj):
        fg_user = self.context.get('request').user
        return fg_user.is_authenticated and Follow.objects.filter(
            user=fg_user, following=obj
        ).exists()
# 
    # def get_recipes(self, obj):
    #     return Recipe.objects.filter(author=obj)

    def validate_username(self, username):
        if username.lower() in RESTRICTED_USERNAMES:
            raise serializers.ValidationError(
                USERNAME_IS_PROHIBITED.format(username=username)
            )
        return super().validate(username)


class AvatarSerializer(UserSerializer):
    """Сериализатор аватара."""

    avatar = Base64ImageField(required=True)

    class Meta(UserSerializer.Meta):
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов."""

    class Meta:
        model = Tag
        fields = '__all__'


class IngredientListSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов."""

    id = serializers.IntegerField(source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')

    # def _get_object(self):
# 
    # def get_name(self, obj):
    #     print('@@@@@@@@@@@@@@@@ self', self)
    #     print('obj:', obj)
    #     return obj.name

    # def get_measurement_unit(self, obj):
    #     return obj.measurement_unit


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов."""

    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True,
        default=serializers.CurrentUserDefault()
    )
    image = Base64ImageField()
    ingredients = IngredientInRecipeSerializer(many=True, write_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        fg_user = self.context.get('request').user
        return fg_user.is_authenticated and fg_user.favorites.filter(
            recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        fg_user = self.context.get('request').user
        return fg_user.is_authenticated and fg_user.shopping_cart.filter(
            recipe=obj
        ).exists()

    def create(self, validated_data):
        # работает
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        for ingredient_data in ingredients_data:
            IngredientRecipe.objects.create(
                ingredient=ingredient_data['id'],
                recipe=recipe,
                amount=ingredient_data['amount']
            )
        return recipe

    def to_representation(self, instance):
        print('1111111111111')
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(
            instance.tags.all(), many=True).data
        print('22222222222', representation)
        representation['ingredients'] = IngredientRecipeSerializer(
            instance.ingredient_recipe.all(), many=True).data
        return representation
