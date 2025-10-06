from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import FgUser, Follow


admin.site.register(FgUser, UserAdmin)
admin.site.register(Follow)
