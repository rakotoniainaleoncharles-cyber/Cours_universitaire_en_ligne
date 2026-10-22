from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + ((None, {'fields': ('role', 'avatar')}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {'fields': ('email', 'first_name', 'last_name', 'role', 'avatar')}),)
