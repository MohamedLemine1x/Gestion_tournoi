from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'type', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Informations supplémentaires', {'fields': ('type',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {'fields': ('email', 'type')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)