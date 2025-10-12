from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .filters import IngredientFilter, RecipeFilter
from .pagination import FgPagination
from .permissions import AuthorOrAuthenticatedOrReadOnly
from .serializers import (
    AddToFavorite, AvatarSerializer, FgUserSerializer,
    FollowSerializer, IngredientListSerializer, RecipeSerializer,
    SubscribtionSerializer, TagSerializer
)
from core.constants import ALREADY_ADDED, NON_EXISTENT_FAV, NOT_ADDED
from recipes.models import (
    Favorite, Ingredient, IngredientRecipe, Recipe, ShoppingCart, Tag
)


User = get_user_model()


class AvatarDetail(APIView):
    """Добавляет/ удаляет аватар."""

    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        serializer = AvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        self.request.user.avatar.delete(save=True)
        self.request.user.avatar = None
        self.request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FgUserViewSet(UserViewSet):
    """
    Сериализатор пользователя.

    Создает пользователя,
    отображает информацию о пользователе,
    добавляет/удаляет подписку на пользователя,
    возвращает список подписок пользователя.
    """

    serializer_class = FgUserSerializer
    pagination_class = FgPagination
    lookup_field = 'id'

    def get_permissions(self):
        if self.action in {
            'get_subscriptions_list',
            'add_to_subscription',
            'delete_subscription',
            'me',
        }:
            return (IsAuthenticated(),)
        return (AllowAny(),)

    def get_serializer_class(self):
        if self.action in {'add_to_subscription', 'delete_subscription'}:
            return FollowSerializer
        if self.action == 'get_subscriptions_list':
            return SubscribtionSerializer
        if self.action == 'set_password' or 'reset_password':
            return super().get_serializer_class()
        return FgUserSerializer

    @action(
        detail=False,
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
                self.get_serializer(page, many=True).data
            )
        return Response(self.get_serializer(
            subscription_list, many=True
        ).data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['recipes_limit'] = self.request.query_params.get(
            'recipes_limit'
        )
        return context

    @action(
        detail=True,
        methods=('post',),
        url_path='subscribe'
    )
    def add_to_subscription(self, request, id=None):
        """Реализует подписку на пользователя."""
        context = self.get_serializer_context()
        context.update({
            'user': self.request.user,
            'following': get_object_or_404(User, id=self.kwargs.get('id'))
        })
        serializer = self.get_serializer(data={}, context=context)
        serializer.is_valid(raise_exception=True)
        follow = serializer.save()

        response_serializer = SubscribtionSerializer(
            follow.following,
            context=self.get_serializer_context()
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    @add_to_subscription.mapping.delete
    def delete_subscription(self, request, id=None):
        """Удаляет подписку на пользователя."""
        serializer = self.get_serializer(
            data={}, context=self.get_context_data()
        )
        serializer.validate_delete()
        self.request.user.follows.filter(following=self.get_object()).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_context_data(self, **kwargs) -> dict[str, any]:
        context = self.get_serializer_context()
        context.update({
            'user': self.request.user,
            'following': get_object_or_404(User, id=self.kwargs.get('id'))
        })
        return context


class IngredientViewSet(ReadOnlyModelViewSet):
    """ViewSet класса Ingredient."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientListSerializer
    filter_backends = (
        DjangoFilterBackend, filters.SearchFilter
    )
    filterset_class = IngredientFilter
    pagination_class = None
    search_fields = ('^name',)


class TagViewSet(ReadOnlyModelViewSet):
    """ViewSet класса Tag."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


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

    def get_permissions(self):
        if self.action in {
            'delete_favorite',
            'delete_from_shopping_cart',
            'download_shopping_cart'
        }:
            return (IsAuthenticated(),)
        if self.request.method in {
            'DELETE',
            'PATCH',
        }:
            return (AuthorOrAuthenticatedOrReadOnly(),)
        return (IsAuthenticatedOrReadOnly(),)

    def perform_create(self, serializer):
        """Автоматически устанавливает пользователя при создании рецепта."""
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        url_path='get-link'
    )
    def get_link(self, request, id=None):
        """Получение короткой ссылки на рецепт."""
        recipe = self.get_object()
        return Response({
            'short-link': request.build_absolute_uri(
                reverse('short-link', args=(recipe.id,))
            )
        })

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
            raise ValidationError(ALREADY_ADDED)

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
            raise ValidationError(NON_EXISTENT_FAV)

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
            raise ValidationError(ALREADY_ADDED)

        ShoppingCart.objects.create(user=user, recipe=recipe)
        return Response(
            self.get_serializer(recipe).data,
            status=status.HTTP_201_CREATED
        )

    @add_to_shopping_cart.mapping.delete  # Лучше один метод с ветвлением мб?
    def delete_from_shopping_cart(self, request, id=None):
        """Удаление рецепта из списка покупок."""
        delete_num, _ = request.user.favorites.filter(
            recipe=self.get_object()
        ).delete()
        if delete_num > 0:
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            raise ValidationError(NOT_ADDED)

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        """Скачивание списка покупок в формате TXT."""
        shopping_cart = self.get_queryset()
        recipes = Recipe.objects.filter(
            id__in=shopping_cart.values('id')
        )
        ingredients = IngredientRecipe.objects.filter(
            recipe__in=recipes
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')

        response = HttpResponse(
            self._generate_shopping_list(
                ingredients, recipes, request.user
            ),
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    def _generate_shopping_list(self, ingredients, recipes, user):
        """Создает дизайн списка покупок."""
        current_date = timezone.localtime()

        CREATED = '📅 Создан:'
        END_TITLE = 'ПРИЯТНЫХ ПОКУПОК!'
        PRODUCT = '   Товар '
        TITLE = '🛒 СПИСОК ПОКУПОК 🛒'
        TOTAL = '🥬 Всего ингредиентов:'
        USER = '👤 Пользователь:'

        WIDTH = 50
        SCALE_WIDTH = 62
        BORDER = '═' * WIDTH
        HEADING_PADDING = 45
        LINE = '─' * WIDTH
        DATE = current_date.strftime("%d.%m.%Y %H:%M")

        text = f'╔{BORDER}╗\n'
        text += f'{TITLE:^{SCALE_WIDTH}}\n'
        text += f'╚{BORDER}╝\n\n'

        text += f'{USER} {user.get_full_name() or user.username}\n'
        text += f'{CREATED} {DATE}\n'
        text += f'{TOTAL} {len(ingredients)}\n\n'

        # Шапка таблицы ингредиентов
        text += f'{PRODUCT}{"Кол-во":>{HEADING_PADDING}}\n'
        text += f' {LINE}\n'

        for ingredient in ingredients:
            name = ingredient.get('ingredient__name')
            unit = ingredient.get('ingredient__measurement_unit')
            amount = ingredient.get('total_amount')

            amount_str = f'{int(amount)}' if amount == int(amount) else (
                f'{amount:.1f}'
            )

            checkbox = '☐'

            # Обрезаем длинные названия ингредиентов
            max_name_length = 30
            display_name = name[:max_name_length - 2] + '...' if (
                len(name) > max_name_length
            ) else name

            # Форматируем название с единицей измерения в скобках
            name_with_unit = f'{checkbox} {display_name} ({unit})'
            quantity = amount_str

            # Вычисляем пробелы для выравнивания
            total_width = 50
            name_width = len(name_with_unit)
            spaces_needed = total_width - name_width

            text += f'{name_with_unit}{" " * spaces_needed}{quantity}\n'

        text += f' {LINE}\n'
        text += 'Отмечайте ☑ купленные товары\n'
        text += '\n'
        text += '\n'
        text += f'╔{BORDER}╗\n'
        text += f'{END_TITLE:^{SCALE_WIDTH}}\n'
        text += f'╚{BORDER}╝\n'
        text += '\n'
        text += f'{"Foodgram 2025":^{SCALE_WIDTH}}\n'
        text += f'{"Ваш помощник в мире рецептов":^{SCALE_WIDTH}}\n'
        return text


def short_link_redirect(request, pk):
    """Редирект по короткой ссылке."""
    get_object_or_404(Recipe, pk=pk)
    return redirect(reverse('recipes-detail', kwargs={'pk': pk}))
