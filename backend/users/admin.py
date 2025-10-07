from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from users.models import Follow


User = get_user_model()


class UserResource(resources.ModelResource):
    """Ресурс для загрузки в модель пользователя."""

    class Meta:
        model = User


@admin.register(User)
class UserAdmin(ImportExportModelAdmin):
    """Административный интерфейс для управления пользователями."""

    resource_class = UserResource
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email')


@admin.register(Follow)
class FollowAdmin(ImportExportModelAdmin):
    """Административный интерфейс для управления подписками."""

    list_display = ('user', 'following')

admin.site.unregister(Group)
