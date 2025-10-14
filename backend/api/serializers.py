import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer
from rest_framework import serializers

from core.constants import (
    ALREADY_ADDED, AMOUNT_MIN_VALUE, CANT_ADD_FOLLOWING, CANT_BE_EMPTY,
    FOLLOWING_VALIDATION, NON_EXISTENT_FAV,
    NON_EXISTENT_SUB, PROHIBITED_VALUE, REPEATED
)
from recipes.models import (
    Favorite, Ingredient, IngredientRecipe, Recipe, ShoppingCart, Tag
)
from users.models import Follow


User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Декодирует картинку и сохраняет ее как файл."""

    def to_internal_value(self, image):
        if isinstance(image, str) and image.startswith('data:image'):
            format, imgstr = image.split(';base64,')
            ext = format.split('/')[-1]
            image = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(image)


class FgUserSerializer(UserSerializer):
    """Сериализатор пользователя."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = (
            'id', 'username', 'first_name', 'last_name', 'email',
            'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, user):
        """Получает значение для флага is_subscribed (fg_user на user)."""
        fg_user = self.context.get('request').user
        return fg_user.is_authenticated and fg_user.follows.filter(
            following=user
        ).exists()


class FgUserWithRecipesSerializer(FgUserSerializer):
    """Сериализатор пользователя с авторскими рецептами."""

    recipes = serializers.SerializerMethodField()

    class Meta(FgUserSerializer.Meta):
        fields = FgUserSerializer.Meta.fields + ('recipes',)

    def get_recipes(self, user):
        return RecipeBriefSerializer(
            user.recipes.all(), many=True, context=self.context
        ).data


class AvatarSerializer(UserSerializer):
    """Сериализатор аватара."""

    avatar = Base64ImageField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = ('avatar',)


class FollowSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания записи в БД (модель Follow).

    - user: username подписчика
    - following: username пользователя, на которого подписываются
    """

    user = serializers.SlugRelatedField(
        slug_field='username',
        read_only=True
    )
    following = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    class Meta:
        model = Follow
        fields = ('user', 'following')

    def validate(self, attrs):
        """Проверяет нет ли дублирования подписки и не подписка на себя."""
        request = self.context['request']
        user = request.user
        following_id = request.resolver_match.kwargs.get('id')
        action = request.method

        if action == 'DELETE':
            if not user.follows.filter(following__id=following_id).exists():
                raise serializers.ValidationError(NON_EXISTENT_SUB)
        else:
            if Follow.objects.filter(
                user=user, following__id=following_id
            ).exists():
                raise serializers.ValidationError(CANT_ADD_FOLLOWING)
            if following_id == user.id:
                raise serializers.ValidationError(FOLLOWING_VALIDATION)
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        following_id = request.resolver_match.kwargs.get('id')
        return Follow.objects.create(
            user=user,
            following_id=following_id
        )


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

    def validate_amount(self, amount):
        if amount < AMOUNT_MIN_VALUE:
            raise serializers.ValidationError(PROHIBITED_VALUE)
        return amount


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


class RecipeBriefSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов краткий."""

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeSerializer(RecipeBriefSerializer):
    """Сериализатор рецептов."""

    author = FgUserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    ingredients = IngredientInRecipeSerializer(many=True, write_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )

    class Meta(RecipeBriefSerializer.Meta):
        fields = RecipeBriefSerializer.Meta.fields + (
            'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'text',
        )

    def get_is_favorited(self, obj):
        """Получает значение для флага is_favorited."""
        fg_user = self.context.get('request').user
        return fg_user.is_authenticated and fg_user.favorites.filter(
            recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        """Получает значение для флага is_in_shopping_cart."""
        fg_user = self.context.get('request').user
        return fg_user.is_authenticated and fg_user.shopping_cart.filter(
            recipe=obj
        ).exists()

    def validate_ingredients(self, ingredients):
        """Проверяет количество и состав ингредиентов."""
        if not ingredients:
            raise serializers.ValidationError(CANT_BE_EMPTY)

        ingredients_id = [ingredient['id'] for ingredient in ingredients]
        if len(ingredients_id) != len(set(ingredients_id)):
            raise serializers.ValidationError(REPEATED)

        return ingredients

    def validate_tags(self, tags):
        """Проверяет добавляемые теги (не должны повторяться, не пусто)."""
        if not tags:
            raise serializers.ValidationError(CANT_BE_EMPTY)
        tags_id = [tag for tag in tags]
        if len(tags_id) != len(set(tags_id)):
            raise serializers.ValidationError(REPEATED)
        return tags

    def create(self, validated_data):
        """Добавляет рецепт в базу данных."""
        ingredients_data = validated_data.pop('ingredients', None)
        tags_data = validated_data.pop('tags', None)

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)

        ingredient_objects = [
            IngredientRecipe(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ]
        IngredientRecipe.objects.bulk_create(ingredient_objects)

        return recipe

    def update(self, instance, validated_data):
        """Обновляет рецепт в базе данных."""
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
        """Добавляет информацию о тегах и ингредиентах в рецепте."""
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(
            instance.tags.all(), many=True).data
        representation['ingredients'] = IngredientRecipeSerializer(
            instance.ingredient_recipe.all(), many=True).data
        return representation


class SelectionSerializer(serializers.ModelSerializer):
    """Сериализатор добавления рецепта в избранное/ список покупок."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        recipe_id = request.resolver_match.kwargs.get('id')
        action = request.resolver_match.url_name
        option = user.favorites if 'favorite' in action else user.shopping_cart

        return option.create(user=user, recipe_id=recipe_id)

    def validate(self, attrs):
        """Проверка от дублирования рецепта в избранном/списке покупок."""
        request = self.context.get('request')
        user = request.user
        recipe_id = request.resolver_match.kwargs.get('id')
        action = request.resolver_match.url_name
        model = Favorite if 'favorite' in action else ShoppingCart

        if request.method == 'DELETE':
            if not model.objects.filter(
                user=user, recipe__id=recipe_id
            ).exists():
                raise serializers.ValidationError(NON_EXISTENT_FAV.format(
                    selection=model._meta.verbose_name.lower()
                ))
        else:
            if model.objects.filter(user=user, recipe__id=recipe_id).exists():
                raise serializers.ValidationError(ALREADY_ADDED.format(
                    selection=model._meta.verbose_name.lower()
                ))
        return attrs


class SubscribtionSerializer(FgUserSerializer):
    """Сериализатор подписок пользователей."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )

    class Meta(FgUserSerializer.Meta):
        fields = FgUserSerializer.Meta.fields + ('recipes_count', 'recipes')

    def get_recipes(self, following):
        """Ограничивает количество выводимых рецептов, если recipes_limit."""
        recipes_limit = self.context.get('recipes_limit')
        recipes = following.recipes.all()
        if recipes_limit:
            try:
                recipes = recipes[:int(recipes_limit)]
            except (TypeError, ValueError):
                pass
        return RecipeBriefSerializer(
            recipes, many=True, context=self.context
        ).data
