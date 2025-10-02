from django.contrib.auth import get_user_model
from django.db import models

from core.constants import CANT_ADD_FAVORITE
from core.text_utils import truncate_with_ellipsis


User = get_user_model()


class Ingredient(models.Model):
    """Модель ингридиентов."""

    name = models.TextField('Название ингридиента', unique=True)
    measurement_unit = models.CharField('Единица измерения', max_length=20)  # Вынести в константы

    class Meta:
        verbose_name = 'ингридиент'
        verbose_name_plural = 'Ингридиенты'
        default_related_name = 'ingridients'
        ordering = ('name',)

    def __str__(self) -> str:
        return truncate_with_ellipsis(self.name)


class Tag(models.Model):
    """Модель тегов."""

    name = models.TextField('Название тега', unique=True)
    slug = models.SlugField('Слаг тега', unique=True)

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        default_related_name = 'tags'
        ordering = ('name',)

    def __str__(self) -> str:
        return truncate_with_ellipsis(self.name)


class Recipe(models.Model):
    """Модель рецептов."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор публикации'
    )
    name = models.TextField('Название', blank=False, null=False)
    image = models.ImageField('Картинка', upload_to='recipe_image/', blank=False, null=False)
    text = models.TextField('Текстовое описание', blank=False, null=False)
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        verbose_name='Список ингредиентов',
        blank=False,
        related_name='recipes'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тег',
        blank=False
    )
    cooking_time = models.SmallIntegerField('Время приготовления (в минутах)', blank=False)
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)
    # is_favorited = models.BooleanField('В избранном')
    # is_in_shopping_cart = models.BooleanField('В списке покупок')

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        return truncate_with_ellipsis(self.name)


class IngredientRecipe(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    amount = models.PositiveSmallIntegerField('Количество')
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='ingredient_recipe'
    )

    def __str__(self) -> str:
        return truncate_with_ellipsis(f'{self.ingredient} {self.recipe}')


class Favorite(models.Model):
    """
    Модель избранных рецептов пользователя.

    - user (ForeignKey): Пользователь, который добавляет рецпт в избранное
    - recipe (ForeignKey): Рецепт, который добавляют в избранное.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='favorites',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранные рецепты'
        # default_related_name = 'favorites'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='recipe_is_already_added',
                violation_error_message=CANT_ADD_FAVORITE
            )
        ]

    def __str__(self) -> str:
        return truncate_with_ellipsis(
            f'{self.user.username}: {self.recipe.name}'
        )


class ShoppingCart(models.Model):
    """
    Модель покупок для рецептов.

    - user: Пользователь, который добавляет рецепт в список покупок
    - recipe: Рецепт, который добавляют в список покупок.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='shopping_cart'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='in_shopping_cart',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'список покупок'
        verbose_name_plural = 'Cписrb покупок'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='recipe_is_already_added_to shopping_cart',
                violation_error_message=CANT_ADD_FAVORITE
            )
        ]

    def __str__(self) -> str:
        return truncate_with_ellipsis(
            f'{self.user.username}: {self.recipe.name}'
        )
