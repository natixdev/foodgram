from django.contrib.auth import get_user_model
from django.db import models

from core.constants import CANT_ADD_FAVORITE
from core.text_utils import truncate_with_ellipsis


User = get_user_model()


class Ingredient(models.Model):
    """Модель ингридиентов."""

    name = models.TextField('Название ингридиента', unique=True)
    measurement_unit = models.TextField('Единица измерения')


class Tag(models.Model):
    """Модель тэгов."""

    name = models.TextField('Название тега', unique=True)
    slug = models.SlugField('Слаг тега', unique=True)


class Recipe(models.Model):
    """Модель рецептов."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор публикации'
    )
    name = models.TextField('Название')
    image = models.ImageField('Картинка', blank=True, null=True)
    text = models.TextField('Текстовое описание')
    ingredients = models.ManyToManyField(
        Ingredient,
        verbose_name='Список ингредиентов'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тег'
    )
    cooking_time = models.IntegerField('Время приготовления (в минутах)')
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'
        ordering = ('-pub_date',)

    def __str__(self) -> str:
        return truncate_with_ellipsis(self.name)


class Favorite(models.Model):
    """
    Модель избранных рецептов пользователя.

    - user (ForeignKey): Пользователь, который добавляет рецпт в избранное
    - favor (ForeignKey): Рецепт, который добавляют в избранное.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    favor = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'favor'),
                name='recipe_is_already_added',
                violation_error_message=CANT_ADD_FAVORITE
            )
        ]

    def __str__(self) -> str:
        return truncate_with_ellipsis(
            f'{self.user.username}: {self.favor.name}'
        )
