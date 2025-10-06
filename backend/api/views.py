from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend, FilterSet, ModelMultipleChoiceFilter, BooleanFilter
from django.shortcuts import render
from djoser.serializers import UserSerializer
from djoser.views import UserViewSet
from rest_framework import filters, generics, status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .serializers import (
    AvatarSerializer, FgUserSerializer, FgUserCreateSerializer,
    FollowSerializer, IngredientListSerializer, RecipeSerializer, 
    SubscribtionSerializer, TagSerializer
)
from recipes.models import Favorite, Ingredient, Recipe, Tag
from users.models import Follow
from .pagination import FgPagination


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
            return [IsAuthenticated(),]
        else:
            return [AllowAny(),]

    def get_serializer_class(self):
        if self.action == 'add_to_subscription':
            return FollowSerializer
        if self.action == 'create':
            return FgUserCreateSerializer
        if self.action == 'get_subscriptions_list':
            return SubscribtionSerializer
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
        follow = self.get_object()
        self.request.user.follows.filter(following=follow).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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


class RecipeFilter(FilterSet):
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
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if value and self.request.user.is_authenticated:
            return queryset.filter(shopping_carts__user=self.request.user)
        return queryset

    # class Meta:
    #     model = Recipe
    #     fields = ['tags', 'author']


class RecipeViewSet(ModelViewSet):
    """ViewSet класса Recipe."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = FgPagination
    lookup_field = 'id'
    http_method_names = ('get', 'post', 'patch', 'delete',)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipeFilter
    filterset_fields = ('name', 'author', 'tags')
    search_fields = ('^name', '^author')
    # permission_classes = (IsAuthenticated, IsAuthorOrReadOnly)

    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     return queryset.with_favorited_and_shopping_cart(self.request.user)

    def get_permissions(self):
        if self.request.method in (
            'PATCH',
            'DELETE',
        ):
            return [IsAuthorOrReadOnly(),]
        else:
            return [IsAuthenticatedOrReadOnly(),]

    def perform_create(self, serializer):
        """Автоматически устанавливает пользователя при создании рецепта."""
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        permission_classes=(AllowAny,),
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
        permission_classes=(IsAuthenticated,),
        # serializer_class=FavoriteSerializer,
        methods=('post',),
        url_path='favorite'
    )
    def add_to_favorite(self, request, id=None):
        """Добавление рецепта в избранное."""
        recipe = self.get_object()
        user = request.user
        # if user.favorites.filter(recipe=recipe).exists():
        #     return Response(
        #         {'errors': 'Рецепт уже в избранном.'},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        Favorite.objects.create(user=user, recipe=recipe)
        return Response(
            {'message': 'Рецепт добавлен в избранное.'},
            status=status.HTTP_201_CREATED
        )

    @add_to_favorite.mapping.delete  # Лучше один метод с ветвлением мб?
    def delete_favorite(self, request, id=None):
        """Удаление рецепта из избранного."""
        recipe = self.get_object()
        self.request.user.favorites.filter(recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

        # elif request.method == 'DELETE':
        #     # Удаляем через related_name
        #     deleted_count, _ = user.favorite_recipes.filter(recipe=recipe).delete()
            
        #     if deleted_count > 0:
        #         return Response(status=status.HTTP_204_NO_CONTENT)
        #     else:
        #         return Response(
        #             {'errors': 'Рецепта нет в избранном.'},
        #             status=status.HTTP_400_BAD_REQUEST
        #         )