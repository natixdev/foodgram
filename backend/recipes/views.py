from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .models import Recipe


def short_link_redirect(request, pk):
    """Редирект по короткой ссылке."""
    return redirect(request.build_absolute_uri(
        f'/recipes/{pk}/'
    ))
