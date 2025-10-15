from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, status
from rest_framework.decorators import action
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
    SelectionSerializer, AvatarSerializer, FgUserSerializer,
    FollowSerializer, IngredientListSerializer, RecipeSerializer,
    SubscribtionSerializer, TagSerializer
)
from recipes.models import (
    Favorite, Ingredient, IngredientRecipe, Recipe, ShoppingCart, Tag
)


User = get_user_model()


class ReadonlyNonPaginated(ReadOnlyModelViewSet):
    """
    Базовый ViewSet для read_only моделей без пагинации.

    Реализует общее поведение для Tag, Ingredients.
    """

    pagination_class = None


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
        return (IsAuthenticated(),) if self.action in {
            'get_subscriptions_list',
            'add_to_subscription',
            'delete_subscription',
            'me',
        } else (AllowAny(),)

    def get_serializer_class(self):
        if self.action in {'add_to_subscription', 'delete_subscription'}:
            return FollowSerializer
        if self.action == 'get_subscriptions_list':
            return SubscribtionSerializer
        if self.action == 'set_password' or 'reset_password':
            return super().get_serializer_class()
        return FgUserSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['recipes_limit'] = self.request.query_params.get(
            'recipes_limit'
        )
        return context

    def _add_to_selection(self):
        serializer = self.get_serializer(
            data={}, context=self.get_serializer_context()
        )
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

    def _delete_user_selection(self, id):
        following = self.get_object()
        serializer = self.get_serializer(data={})
        serializer.is_valid(raise_exception=True)
        self.request.user.follows.filter(following=following).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        url_path='subscriptions',
    )
    def get_subscriptions_list(self, request):
        """Возвращает список подписок пользователя."""
        subscription_list = User.objects.filter(followers__user=request.user)
        page = self.paginate_queryset(subscription_list)
        return self.get_paginated_response(
            self.get_serializer(page, many=True).data
        )

    @action(
        detail=True,
        methods=('post',),
        url_path='subscribe'
    )
    def add_to_subscription(self, request, id=None):
        """Реализует подписку на пользователя."""
        get_object_or_404(User, id=id)
        return self._add_to_selection()

    @add_to_subscription.mapping.delete
    def delete_subscription(self, request, id=None):
        """Удаляет подписку на пользователя."""
        return self._delete_user_selection(id)


class IngredientViewSet(ReadonlyNonPaginated):
    """ViewSet класса Ingredient."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientListSerializer
    filter_backends = (
        DjangoFilterBackend, filters.SearchFilter
    )
    filterset_class = IngredientFilter
    search_fields = ('^name',)


class TagViewSet(ReadonlyNonPaginated):
    """ViewSet класса Tag."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


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

    def get_serializer_class(self):
        if self.action in {
            'add_to_favorite',
            'delete_favorite',
            'add_to_shopping_cart',
            'delete_from_shopping_cart',
        }:
            return SelectionSerializer
        return RecipeSerializer

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
                reverse('recipes:short-link', args=(recipe.id,))
            )
        })

    def _add_to_selection(self, request, id, model):
        recipe = self.get_object()
        serializer = self.get_serializer(data={
            'id': recipe.id,
            'name': recipe.name,
            'image': recipe.image,
            'cooking_time': recipe.cooking_time
        })
        serializer.is_valid(raise_exception=True)
        selection_item = serializer.save()

        response_serializer = self.get_serializer(
            selection_item.recipe,
            context=self.get_serializer_context()
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def _delete_user_selection(self, request, id, model):
        recipe = get_object_or_404(Recipe, id=id)
        serializer = self.get_serializer(data={
            'id': recipe.id,
            'name': recipe.name,
            'image': recipe.image,
            'cooking_time': recipe.cooking_time
        })
        serializer.is_valid(raise_exception=True)
        model.objects.filter(user=self.request.user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post',),
        url_path='favorite'
    )
    def add_to_favorite(self, request, id=None):
        """Добавление рецепта в избранное."""
        return self._add_to_selection(request, id, Favorite)

    @add_to_favorite.mapping.delete
    def delete_favorite(self, request, id=None):
        """Удаление рецепта из избранного."""
        return self._delete_user_selection(request, id, Favorite)

    @action(
        detail=True,
        methods=('post',),
        url_path='shopping_cart'
    )
    def add_to_shopping_cart(self, request, id=None):
        """Добавление рецепта в список покупок."""
        return self._add_to_selection(request, id, ShoppingCart)

    @add_to_shopping_cart.mapping.delete
    def delete_from_shopping_cart(self, request, id=None):
        """Удаление рецепта из списка покупок."""
        return self._delete_user_selection(request, id, ShoppingCart)

    @action(detail=False, methods=('get',))
    def download_shopping_cart(self, request):
        """Скачивание списка покупок в формате TXT."""
        shopping_cart = self.get_queryset()
        recipes = Recipe.objects.filter(id__in=shopping_cart.values('id'))
        ingredients = IngredientRecipe.objects.filter(
            recipe__in=recipes.filter(in_shoppingcart__user=request.user)
        ).values('recipe').values(
            name=F('ingredient__name'),
            measurement_unit=F('ingredient__measurement_unit')
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
        HEADING_PADDING = 40
        LINE = '─' * WIDTH
        DATE = current_date.strftime('%d.%m.%Y %H:%M')
        user = user.get_full_name() or user.username
        length = len(ingredients)

        text = f'╔{BORDER}╗\n'
        text += f'{TITLE:^{SCALE_WIDTH}}\n'
        text += f'╚{BORDER}╝\n\n'

        text += f'{USER} {user}\n'
        text += f'{CREATED} {DATE}\n'
        text += f'{TOTAL} {length}\n\n'

        # Шапка таблицы ингредиентов
        text += f'{PRODUCT}{"Кол-во":>{HEADING_PADDING}}\n'
        text += f' {LINE}\n'

        for ingredient in ingredients:
            name = ingredient.get('name')
            unit = ingredient.get('measurement_unit')
            amount = int(ingredient.get('total_amount'))

            amount_str = str(amount) if amount == int(amount) else (
                f'{amount:.1f}'
            )

            checkbox = '☐'

            # Обрезаем длинные названия ингредиентов
            max_name_length = 30
            cuted_name = name[:max_name_length - 2]
            display_name = f'{cuted_name}...' if (
                len(name) > max_name_length
            ) else name

            # Форматируем название с единицей измерения в скобках
            name_with_unit = f'{checkbox} {display_name} ({unit})'
            quantity = amount_str

            # Вычисляем пробелы для выравнивания
            total_width = 45
            name_width = len(name_with_unit)
            spaces_needed = total_width - name_width
            space = ' ' * spaces_needed

            text += f'{name_with_unit}{space}{quantity}\n'

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
