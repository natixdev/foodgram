from django_filters.rest_framework import (
    BooleanFilter, CharFilter, FilterSet, ModelMultipleChoiceFilter
)

from recipes.models import Ingredient, Recipe, Tag


class RecipeFilter(FilterSet):
    """Фильтр объектов модели рецептов Recipe."""

    tags = ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    is_favorited = BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = BooleanFilter(
        method='filter_is_in_shopping_cart'
    )

    class Meta:
        model = Recipe
        fields = ('tags', 'is_favorited', 'is_in_shopping_cart', 'author')

    def filter_is_favorited(self, queryset, name, value):
        """Дополнительная фильтрация, если установлен флаг is_favorited."""
        if value and self.request.user.is_authenticated:
            return queryset.filter(in_favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Доп. фильтрация, если установлен флаг is_in_shopping_cart."""
        if value and self.request.user.is_authenticated:
            return queryset.filter(in_shopping_cart__user=self.request.user)
        return queryset


class IngredientFilter(FilterSet):
    """Фильтр для ингредиентов."""

    name = CharFilter(
        field_name='name',
        method='filter_name',
        lookup_expr='istartswith',
    )

    class Meta:
        model = Ingredient
        fields = ('name',)

    def filter_name(self, queryset, _name, value):
        """Фильтрация по названию ингредиента (нечувствительная к регистру)."""
        if not value:
            return queryset

        normalized_value = value.strip()
        if not normalized_value:
            return queryset

        return queryset.filter(name__istartswith=normalized_value)
