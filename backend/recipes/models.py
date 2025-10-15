from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

from core.constants import (
    ALREADY_ADDED, ALREADY_ADDED_INGREDIENT, COOKING_TIME_MIN_VALUE
)
from core.text_utils import truncate_with_ellipsis


User = get_user_model()


class Ingredient(models.Model):
    """Модель ингредиентов."""

    name = models.TextField('Название ингредиента', unique=True)
    measurement_unit = models.CharField('Единица измерения', max_length=20)

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'ингредиенты'
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
        verbose_name='Автор публикации',
    )
    name = models.CharField('Название', max_length=256)
    image = models.ImageField('Картинка', upload_to='recipe_image/')
    text = models.TextField('Текстовое описание')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        verbose_name='Список ингредиентов',
        related_name='recipes'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тег',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах',
        validators=(MinValueValidator(
            COOKING_TIME_MIN_VALUE,
            message=f'Минимум {COOKING_TIME_MIN_VALUE}'
        ),),
        help_text='Время приготовления в минутах.'
    )
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        return truncate_with_ellipsis(self.name)


class IngredientRecipe(models.Model):
    """Промежуточная таблица для добавления количества ингредиента в рецепт."""

    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент')
    amount = models.PositiveSmallIntegerField('Количество')
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_recipe',
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'ингредиенты для рецепта'
        verbose_name_plural = 'Ингредиенты рецептов'
        constraints = [
            models.UniqueConstraint(
                fields=('ingredient', 'recipe'),
                name='ingredient_is_already_added',
                violation_error_message=ALREADY_ADDED_INGREDIENT
            )
        ]

    def __str__(self) -> str:
        return truncate_with_ellipsis(f'{self.ingredient} {self.recipe}')


class AbstractSelection(models.Model):
    """
    Абстрактная модель для моделей Favorite и ShoppingCart.

    - user (FK): Пользователь, который добавляет рецпт в избранное.
    - recipe (FK): Рецепт, который добавляют в избранное/список покупок.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='%(class)ss',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='in_%(class)s',
        blank=True,
        null=True
    )

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return truncate_with_ellipsis(
            f'{self.user.username}: {self.recipe.name}'
        )


class Favorite(AbstractSelection):
    """Модель избранных рецептов пользователя."""

    class Meta(AbstractSelection.Meta):
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='recipe_is_already_added',
                violation_error_message=ALREADY_ADDED
            )
        ]


class ShoppingCart(AbstractSelection):
    """Модель покупок для рецептов."""

    class Meta(AbstractSelection.Meta):
        verbose_name = 'список покупок'
        verbose_name_plural = 'Cписок покупок'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='recipe_is_already_added_to shopping_cart',
                violation_error_message=ALREADY_ADDED
            )
        ]
