from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, ModelMultipleChoiceFilter, BooleanFilter
from django.shortcuts import render
from djoser.serializers import UserSerializer
from djoser.views import UserViewSet
from rest_framework import filters, generics, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .serializers import (
    AddToFavorite, AvatarSerializer, FgUserSerializer, FgUserCreateSerializer,
    FollowSerializer, IngredientListSerializer, RecipeSerializer,
    SubscribtionSerializer, TagSerializer
)
from recipes.models import Favorite, Ingredient, IngredientRecipe, ShoppingCart, Recipe, Tag
from users.models import Follow
from .pagination import FgPagination

from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from django.db.models import Sum, F
from django.utils import timezone


User = get_user_model()


# !!!!!!!!!!УБРАТЬ
from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Разрешение на изменение только для автора.
    Остальные могут только читать.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions are only allowed to the author
        return obj.author == request.user


class AvatarDetail(APIView):
    """Добавляет/ удаляет аватар."""

    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        serializer = AvatarSerializer(request.user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        self.request.user.avatar.delete(save=True)
        self.request.user.avatar = None
        self.request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FgUserViewSet(UserViewSet):
    """."""

    serializer_class = FgUserSerializer
    pagination_class = FgPagination
    lookup_field = 'id'

    def get_permissions(self):
        if self.action in (
            'get_subscriptions_list',
            'add_to_subscription',
            'delete_subscription',
            'me',
        ):
            return (IsAuthenticated(),)
        else:
            return (AllowAny(),)

    def get_serializer_class(self):
        if self.action == 'add_to_subscription':
            return FollowSerializer
        if self.action == 'create':
            return FgUserCreateSerializer
        if self.action == 'get_subscriptions_list':
            return SubscribtionSerializer
        if self.action == 'set_password' or 'reset_password':
            return super().get_serializer_class()
        return FgUserSerializer

    @action(
        detail=False,
        methods=('get',),
        url_path='subscriptions',
    )
    def get_subscriptions_list(self, request):
        """Возвращает список подписок пользователя."""
        subscription_list = [
            sub.following for sub in request.user.follows.all()
        ]
        page = self.paginate_queryset(subscription_list)
        if page:
            return self.get_paginated_response(
                self.get_serializer(page, many=True, context={
                    'request': request,
                    'recipes_limit': request.GET.get('recipes_limit')
                }).data
            )
        return Response(self.get_serializer(
            subscription_list, many=True
        ).data)

    @action(
        detail=True,
        methods=('post',),
        url_path='subscribe'
    )
    def add_to_subscription(self, request, id=None):
        """."""
        user = self.request.user
        following = self.get_object()

        serializer = self.get_serializer(
            data={
                'user': user,
                'following': following
            },
            context={
                'request': request
            }
        )

        if serializer.is_valid():
            return Response(SubscribtionSerializer(
                Follow.objects.create(
                    user=user, following=following
                ).following, context={
                    'request': request,
                    'recipes_limit': request.GET.get('recipes_limit')
                }
            ).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @add_to_subscription.mapping.delete  # Лучше один метод с ветвлением мб?
    def delete_subscription(self, request, id=None):
        """."""
        delete_num, _ = self.request.user.follows.filter(
            following=self.get_object()).delete()
        if delete_num > 0:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError('Вы не подписаны на этого пользоавтеля в константу')


class IngredientViewSet(
    # ModelViewSet
    ReadOnlyModelViewSet
):
    """ViewSet класса Ingredient."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientListSerializer
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    pagination_class = None
    filterset_fields = ('name',)
    search_fields = ('^name',)


class TagViewSet(
    # ModelViewSet
    ReadOnlyModelViewSet
):
    """ViewSet класса Tag."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (AllowAny,)


class RecipeFilter(FilterSet):  # вынести
    """Фильтр для рецептов."""

    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        # conjoined=False
    )
    is_favorited = BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ('tags', 'is_favorited', 'is_in_shopping_cart', 'author')

    def filter_is_favorited(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(in_favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(in_shopping_cart__user=self.request.user)
        return queryset


class RecipeViewSet(ModelViewSet):
    """ViewSet класса Recipe."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = FgPagination
    lookup_field = 'id'
    http_method_names = ('get', 'post', 'patch', 'delete', 'retrieve')
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipeFilter
    filterset_fields = ('name', 'author', 'tags')
    search_fields = ('^name', '^author')
    # permission_classes = (IsAuthenticated, IsAuthorOrReadOnly)

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset
        # return queryset.with_favorited_and_shopping_cart(self.request.user)

    def get_permissions(self):
        if self.action in ('delete_favorite', 'delete_from_shopping_cart', 'download_shopping_cart'):
            return (IsAuthenticated(),)
        elif self.request.method in (
            'PATCH',
            'DELETE',
        ):
            return (IsAuthorOrReadOnly(),)
        else:
            return (IsAuthenticatedOrReadOnly(),)

    def perform_create(self, serializer):
        """Автоматически устанавливает пользователя при создании рецепта."""
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        # permission_classes=(AllowAny,),
        # serializer_class=LinkSerializer,
        methods=('get',),
        url_path='get-link'
    )
    def get_link(self, request, id=None):
        """Получение короткой ссылки на рецепт."""
        # return Response(self.get_serializer(request.pk).data
        recipe = self.get_object()
        return Response(
            {'short-link': f'https://foodgram.example.org/api/recipes/{recipe.id}'}
        )
        # Добавить Exceptions и изменить доменное имя

    @action(
        detail=True,
        serializer_class=AddToFavorite,
        methods=('post',),
        url_path='favorite'
    )
    def add_to_favorite(self, request, id=None):
        """Добавление рецепта в избранное."""
        recipe = self.get_object()
        user = request.user
        if user.favorites.filter(recipe=recipe).exists():
            raise ValidationError('Рецепт уже в избранном надо вынести в константу')

        Favorite.objects.create(user=user, recipe=recipe)
        return Response(
            self.get_serializer(recipe).data,
            status=status.HTTP_201_CREATED
        )

    @add_to_favorite.mapping.delete  # Лучше один метод с ветвлением мб?
    def delete_favorite(self, request, id=None):
        """Удаление рецепта из избранного."""
        recipe = self.get_object()
        user = request.user
        delete_num, _ = user.favorites.filter(recipe=recipe).delete()
        if delete_num > 0:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError('Рецепт не был добавлен в избранное в константу')

    @action(
        detail=True,
        serializer_class=AddToFavorite,
        methods=('post',),
        url_path='shopping_cart'
    )
    def add_to_shopping_cart(self, request, id=None):
        """Добавление рецепта в список покупок."""
        recipe = self.get_object()
        user = request.user
        if user.shopping_cart.filter(recipe=recipe).exists():
            raise ValidationError('Рецепт уже добавлен в список покупок надо вынести в константу')

        ShoppingCart.objects.create(user=user, recipe=recipe)
        return Response(
            self.get_serializer(recipe).data,
            status=status.HTTP_201_CREATED
        )

    @add_to_shopping_cart.mapping.delete  # Лучше один метод с ветвлением мб?
    def delete_from_shopping_cart(self, request, id=None):
        """Удаление рецепта из избранного."""
        delete_num, _ = request.user.favorites.filter(
            recipe=self.get_object()
        ).delete()
        if delete_num > 0:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError('Рецепт не был добавлен в список покупок в константу')

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        """Скачивание списка покупок в формате TXT."""
        shopping_cart = self.get_queryset()
        print('111111111111', shopping_cart)
        recipes = Recipe.objects.filter(
            id__in=shopping_cart.values('id')
        )
        print('222222222222', recipes)
        ingredients = IngredientRecipe.objects.filter(
            recipe__in=recipes
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')
        print('3333333333333333', ingredients)

        response = HttpResponse(
            self._generate_shopping_list(ingredients, recipes, request.user),
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    def _generate_shopping_list(self, ingredients, recipes, user):
        """Создает дизайн списка покупок."""

        current_date = timezone.now().strftime('%d.%m.%Y %H:%M')
        width = 64
        border = '═' * width
        line = '─' * width
        list_title = '🛒 СПИСОК ПОКУПОК 🛒'
        title_gap = (width - len(list_title)) // 2
        space = ' '
        WIDTH = 64
        BORDER = "═" * WIDTH
        LINE = "─" * WIDTH
        TITLE_PADDING = 21
        CENTER_PADDING = 22
        INDENT = 15

        text = f'╔{border}╗\n'
        text += f'{space * title_gap}{list_title}{space * title_gap}\n'
        text += f'╚{border}╝\n\n'

        text += f'👤 Пользователь: {user.get_full_name() or user.username}\n'
        text += f'📅 Создан: {current_date}\n'
        text += f'🥬 Всего ингредиентов: {len(ingredients)}\n\n'

        # Шапка таблицы ингредиентов
        text += f' Товар{' ' * 40}Кол-во\n'
        text += f' {line}\n'

        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            unit = ingredient['ingredient__measurement_unit']
            amount = ingredient['total_amount']

            amount_str = f'{int(amount)}' if amount == int(amount) else f'{amount:.1f}'

            checkbox = '☐'

            # Обрезаем длинные названия ингредиентов
            max_name_length = 25
            if len(name) > max_name_length:
                display_name = name[:max_name_length-2] + '...'
            else:
                display_name = name

            # Форматируем название с единицей измерения в скобках
            name_with_unit = f'{checkbox} {display_name} ({unit})'
            quantity = f'{amount_str}'

            # Вычисляем пробелы для выравнивания
            total_width = 50
            name_width = len(name_with_unit)
            spaces_needed = total_width - name_width

            text += f'{name_with_unit}{' ' * spaces_needed}{quantity}\n'

        text += ' ' + LINE + '\n'
        text += 'Отмечайте ☑ купленные товары\n'
        text += '\n'
        text += f'╔{BORDER}╗\n'
        text += ' ' * CENTER_PADDING + 'ПРИЯТНЫХ ПОКУПОК!' + ' ' * CENTER_PADDING + '\n'
        text += f'╚{BORDER}╝\n'
        text += '\n'
        text += ' ' * CENTER_PADDING + '🍣🥢 Foodgram 2025\n'
        text += ' ' * INDENT + 'Ваш помощник в мире рецептов\n'

        return text
