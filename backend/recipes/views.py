from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .models import Recipe


def short_link_redirect(request, id):
    """Редирект по короткой ссылке."""
    recipe = get_object_or_404(Recipe, id=id)
    return redirect(reverse('recipes-detail', kwargs={'id': recipe.id}))
