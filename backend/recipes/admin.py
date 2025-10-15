from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Count
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import (
    Favorite, Ingredient, IngredientRecipe, Recipe, ShoppingCart, Tag
)

User = get_user_model()


class FavoriteInline(admin.TabularInline):
    """Inline для отображения добавлений в избранное."""

    model = Favorite
    extra = 0
    readonly_fields = ('user',)
    can_delete = False


class IngredientsResource(resources.ModelResource):
    """Ресурс для загрузки в модель Ingredients."""

    class Meta:
        model = Ingredient


@admin.register(Ingredient)
class IngredientAdmin(ImportExportModelAdmin):
    """Административный интерфейс для управления ингредиентами."""

    list_display = ('name', 'measurement_unit')
    list_display_links = ('name',)
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


@admin.register(Tag)
class TagAdmin(ImportExportModelAdmin):
    """Административный интерфейс для управления тегами."""

    list_display = ('name', 'slug')
    list_display_links = ('name',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class RecipeIngredientInline(admin.TabularInline):
    """Inline ингредиентов в рецепте."""

    model = IngredientRecipe
    extra = 1
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(ImportExportModelAdmin):
    """Административный интерфейс для управления рецептами."""

    list_display = ('name', 'author', 'favorites_count')
    list_display_links = ('name', 'author')
    search_fields = (
        'name',
        'author__username', 'author__email')
    list_filter = ('tags',)
    readonly_fields = ('favorites_count_display',)
    filter_horizontal = ('tags',)
    inlines = (RecipeIngredientInline,)

    @admin.display(description='В избранном', ordering='favorites_count')
    def favorites_count(self, recipe):
        return getattr(recipe, 'favorites_count', 0)

    @admin.display(description='Общее число добавлений в избранное')
    def favorites_count_display(self, recipe):
        return recipe.favorites.count()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(favorites_count=Count('in_favorites'))


class BaseSelectionAdmin(ImportExportModelAdmin):
    """Базовый административный интерфейс для Favorite и ShoppingCart."""
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(Favorite)
class FavoriteAdmin(BaseSelectionAdmin):
    """Административный интерфейс для управления избранными рецептами."""


@admin.register(ShoppingCart)
class ShoppingCartAdmin(BaseSelectionAdmin):
    """Административный интерфейс для управления списком покупок."""
