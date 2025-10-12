from rest_framework import permissions


class AuthorOrAuthenticatedOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    """Разрешает доступ автору, зарегистрированному или только чтение."""

    def has_object_permission(self, request, view, recipe):
        return (
            request.method in permissions.SAFE_METHODS or (
                recipe.author == request.user
            )
        )
