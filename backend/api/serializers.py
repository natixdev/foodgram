import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from core.constants import RESTRICTED_USERNAMES, USERNAME_IS_PROHIBITED
from recipes.models import Ingredient, Recipe, Tag
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


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингридиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор рецептов."""

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'tags', 'image', 'name', 'text', 'cooking_time'
        )
