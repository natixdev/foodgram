from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .models import Recipe


def short_link_redirect(request, pk):
    """Редирект по короткой ссылке."""
    get_object_or_404(Recipe, pk=pk)
    return redirect(f'/recipes/{pk}')
