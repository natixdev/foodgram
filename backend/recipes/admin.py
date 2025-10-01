from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Favorite, Ingredient, Tag, Recipe


admin.site.register(Favorite)
admin.site.register(Ingredient)
admin.site.register(Tag)
admin.site.register(Recipe)

# Тут можно навертеть по-красивее
