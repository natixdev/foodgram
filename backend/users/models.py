from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models

from core.text_utils import truncate_with_ellipsis
from core.constants import FOLLOWING_VALIDATION


class FgUser(AbstractUser):
    """Расширяет абстрактную модель пользователя."""

    email = models.EmailField('Эл. почта', unique=True)
    avatar = models.ImageField(
        'Аватар', upload_to='avatars/', null=True, blank=True
    )
    first_name = models.CharField('Имя', max_length=150)
    last_name = models.CharField('Фамилия', max_length=150)
    username = models.CharField(
        'Логин',
        max_length=150,
        unique=True,
        validators=(UnicodeUsernameValidator(),)
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('-date_joined',)

    def __str__(self) -> str:
        return truncate_with_ellipsis(self.username)


User = get_user_model()


class Follow(models.Model):
    """
    Модель подписок пользователей друг на друга.

    - user (ForeignKey): Пользователь, который подписывается
    - following (ForeignKey): Пользователь, на которого подписываются.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follows',
        verbose_name='Пользователь'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Подписки',
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.CheckConstraint(
                check=~models.Q(user=models.F('following')),
                name='user_cant_follow_himself',
                violation_error_message=FOLLOWING_VALIDATION
            ),
            models.UniqueConstraint(
                fields=('user', 'following'),
                name='following_already_exists',
            )
        ]

    def __str__(self) -> str:
        return truncate_with_ellipsis(
            f'{self.user.username}: {self.following.username}'
        )
