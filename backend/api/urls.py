from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AvatarDetail, IngredientViewSet, RecipeViewSet, TagViewSet, FgUserViewSet,
    short_link_redirect
)


v1_router = DefaultRouter()
v1_router.register('ingredients', IngredientViewSet, basename='ingredients')
v1_router.register('tags', TagViewSet, basename='tags')
v1_router.register('recipes', RecipeViewSet, basename='recipes')


me_urlpatterns = [
    path('', FgUserViewSet.as_view({
        'get': 'me'
    })),
    path('avatar/', AvatarDetail.as_view())
]

users_urlpatterns = [
    path('', FgUserViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('subscriptions/', FgUserViewSet.as_view({
        'get': 'get_subscriptions_list'
    })),
    path('<int:id>/', FgUserViewSet.as_view({
        'get': 'retrieve'
    })),
    path('<int:id>/subscribe/', FgUserViewSet.as_view({
        'post': 'add_to_subscription',
        'delete': 'delete_subscription'
    })),
    path('me/', include(me_urlpatterns)),
    path('set_password/', FgUserViewSet.as_view({
        'post': 'set_password'
    })),
]


urlpatterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(v1_router.urls)),
    path('users/', include(users_urlpatterns)),
    path('s/<int:pk>/', short_link_redirect, name='short-link'),
]
