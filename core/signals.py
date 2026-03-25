from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Badge, Message, Resume
from django.contrib.auth.password_validation import validate_password
from django.dispatch import receiver
from django.db.models import Sum
from django.db.models.signals import post_save, post_delete

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ("user", "full_name", "phone", "avatar", "avatar_url", "about", "xp")

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        if obj.avatar and hasattr(obj.avatar, "url"):
            return request.build_absolute_uri(obj.avatar.url)
        return None

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ("id", "title", "created_at")

class MessageSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ("id","from_user","to_user","text","attachment","created_at","read")

class ResumeSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = ("id","user","filename","file","file_url","status","created_at")
        read_only_fields = ("user","status","created_at","filename")

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and hasattr(obj.file, "url"):
            return request.build_absolute_uri(obj.file.url)
        return None


@receiver([post_save, post_delete], sender=Badge)
def update_user_xp(sender, instance, **kwargs):
    user = instance.user

    total_xp = Badge.objects.filter(user=user).aggregate(
        total=Sum("xp_count")
    )["total"] or 0

    profile = user.profile
    profile.xp = total_xp
    profile.save()