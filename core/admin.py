from django.contrib import admin
from .models import Profile, Message, Resume, Badge

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "full_name", "phone", "role", "xp", "created_at")
    search_fields = ("full_name", "user__email", "phone")
    readonly_fields = ("created_at",)

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at")

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "from_user", "to_user", "created_at", "read")
    search_fields = ("from_user__email", "to_user__email", "text")

@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "filename", "created_at")
    readonly_fields = ("created_at",)
