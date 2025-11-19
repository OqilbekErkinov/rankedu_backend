from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Message, Resume, Badge
from django.core.files.base import ContentFile
import base64, uuid

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "is_active")

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        # model dagi haqiqiy maydonlarni yozing — 'bio' yo'q bo'lsa olib tashlang
        fields = ("id", "user", "full_name", "phone", "avatar", "avatar_url", "xp", "role", "created_at")
        read_only_fields = ("created_at",)

    def get_avatar_url(self, obj):
        request = self.context.get("request")
        if obj.avatar:
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

class RegisterSerializer(serializers.Serializer):
    fullname = serializers.CharField(max_length=255, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    avatarDataUrl = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        from django.contrib.auth.models import User
        email = validated_data["email"].lower()
        password = validated_data["password"]
        username = email.split("@")[0]
        user = User.objects.create_user(username=username, email=email, password=password)
        profile = Profile.objects.create(
            user=user,
            full_name=validated_data.get("fullname",""),
            phone=validated_data.get("phone","")
        )
        avatar_data = validated_data.get("avatarDataUrl")
        if avatar_data:
            try:
                header, base64data = avatar_data.split(",", 1)
                fmt = header.split(";")[0].split("/")[1]
                filename = f"avatar_{uuid.uuid4().hex}.{fmt}"
                data = ContentFile(base64.b64decode(base64data), name=filename)
                profile.avatar.save(filename, data, save=True)
            except Exception:
                # do not raise — silently ignore invalid avatarDataUrl
                pass
        profile.save()
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ("id", "title", "description", "icon", "created_at")

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = "__all__"

class ResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = "__all__"
