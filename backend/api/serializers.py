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
    """Сериализатор ингредиентов для вывода списка ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов для добавления ингредиентов в рецепт."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'amount')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов для вывода ингредиентов в рецепте."""

    id = serializers.IntegerField(source='ingredient.id', read_only=True)
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов."""

    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = FgUserSerializer(read_only=True)
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

    def validate_cooking_time(self, minutes):
        if minutes < 1:
            raise serializers.ValidationError('Не может быть меньше 1')
        return minutes

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError('Не может быть пустым')

        if not all(ingredient['amount'] >= 1 for ingredient in ingredients):
            raise serializers.ValidationError('Не может быть меньше 1')

        ingredients_id = [ingredient['id'].id for ingredient in ingredients]
        if len(ingredients_id) != len(set(ingredients_id)):
            raise serializers.ValidationError('Не должны повторяться')

        return ingredients

    def validate_tags(self, tags):
        if not tags:
            raise serializers.ValidationError('Не может быть пустым')
        tags_id = [tag for tag in tags]
        if len(tags_id) != len(set(tags_id)):
            raise serializers.ValidationError('Не должны повторяться')
        return tags

    def create(self, validated_data):
        # работает
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        for ingredient_data in ingredients_data:
            IngredientRecipe.objects.create(
                ingredient=ingredient_data['id'],
                recipe=recipe,
                amount=ingredient_data['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        self.validate_ingredients(ingredients_data)
        self.validate_tags(tags_data)

        if tags_data:
            instance.tags.set(tags_data)

        if ingredients_data:
            instance.ingredient_recipe.all().delete()

            for ingredient_data in ingredients_data:
                IngredientRecipe.objects.create(
                    ingredient=ingredient_data['id'],
                    recipe=instance,
                    amount=ingredient_data['amount']
                )
        for data, value in validated_data.items():
            setattr(instance, data, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(
            instance.tags.all(), many=True).data
        representation['ingredients'] = IngredientRecipeSerializer(
            instance.ingredient_recipe.all(), many=True).data
        return representation
