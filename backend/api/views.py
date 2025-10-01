from django.contrib.auth import get_user_model
from django.shortcuts import render
from djoser.serializers import UserSerializer
from djoser.views import UserViewSet
from rest_framework import generics, status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .serializers import AvatarSerializer, IngredientSerializer, RecipeSerializer, TagSerializer, FgUserSerializer
from recipes.models import Favorite, Ingredient, Recipe, Tag
from users.models import Follow


User = get_user_model()


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
    pagination_class = LimitOffsetPagination
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

    @action(
        detail=False,
        methods=('get',),
        url_path='subscriptions'
    )
    def get_subscriptions_list(self, request):
        """Возвращает список подписок пользователя."""
        user = request.user
        subscriptions = user.follows.all()
        return Response(
            {
                'results': subscriptions
            },
            status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=('post',),
        url_path='subscribe'
    )
    def add_to_subscription(self, request, id=None):
        """."""
        follow = self.get_object()
        user = self.request.user
        # if user.favorites.filter(recipe=recipe).exists():
        #     return Response(
        #         {'errors': 'Рецепт уже в избранном.'},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        Follow.objects.create(user=user, following=follow)
        return Response(f'созд', status=status.HTTP_201_CREATED)

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
    serializer_class = IngredientSerializer
    pagination_class = None
    permission_classes = (AllowAny,)


class TagViewSet(
    # ModelViewSet
    ReadOnlyModelViewSet
):
    """ViewSet класса Tag."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    permission_classes = (AllowAny,)


class RecipeViewSet(ModelViewSet):
    """ViewSet класса Recipe."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = LimitOffsetPagination
    lookup_field = 'id'
    http_method_names = ('get', 'post', 'patch', 'delete',)

    @action(
        detail=True,
        permission_classes=(IsAuthenticated,),
        # serializer_class=LinkSerializer,
        methods=('get',),
        url_path='get-link'
    )
    def get_link(self, request):
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