# core/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Badge, Message, Resume


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class ProfileSerializer(serializers.ModelSerializer):
    # nested user info
    user = UserSerializer(read_only=True)

    # convenience / frontend-friendly fields (computed)
    user_id = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    university_short = serializers.SerializerMethodField()
    university_full = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    major = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        # hamma fieldlarni olamiz – noto‘g‘ri nom yozib yubormaslik uchun
        fields = "__all__"
        read_only_fields = ("user", "user_id", "avatar_url", "full_name")

    def get_user_id(self, obj):
        try:
            return obj.user.id
        except Exception:
            return getattr(obj, "user_id", None)

    def get_avatar_url(self, obj):
        request = (
            self.context.get("request") if isinstance(self.context, dict) else None
        )
        url = None

        if hasattr(obj, "avatar") and getattr(obj, "avatar"):
            try:
                url = obj.avatar.url
            except Exception:
                url = getattr(obj, "avatar", None)

        if not url:
            url = getattr(obj, "avatar_url", None) or getattr(obj, "avatarUrl", None)
            if callable(url):
                try:
                    url = url()
                except Exception:
                    url = None

        if url and request and isinstance(url, str) and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url

    def _first_existing_attr(self, obj, candidates):
        for name in candidates:
            if hasattr(obj, name):
                v = getattr(obj, name)
                if v not in (None, ""):
                    return v
        meta = getattr(obj, "meta", None)
        if isinstance(meta, dict):
            for name in candidates:
                if meta.get(name):
                    return meta[name]
        return None

    def get_university_short(self, obj):
        return self._first_existing_attr(
            obj,
            [
                "university_short",
                "universityShort",
                "university_short_name",
                "university",
                "school",
            ],
        )

    def get_university_full(self, obj):
        return self._first_existing_attr(
            obj,
            [
                "university_full",
                "universityFull",
                "university_full_name",
                "university_name",
                "university",
            ],
        )

    def get_full_name(self, obj):
        candidates = ["full_name", "fullname", "name"]
        val = self._first_existing_attr(obj, candidates)
        if val:
            return val
        user = getattr(obj, "user", None)
        if user:
            fn = (getattr(user, "first_name", "") or "").strip()
            ln = (getattr(user, "last_name", "") or "").strip()
            full = f"{fn} {ln}".strip()
            if full:
                return full
            return getattr(user, "username", None) or (
                getattr(user, "email", "") or ""
            ).split("@")[0]
        return None

    def get_major(self, obj):
        return self._first_existing_attr(
            obj, ["major", "speciality", "specialization", "field", "degree"]
        )


class BadgeSerializer(serializers.ModelSerializer):
    proof_url = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        # modeldagi field nomlariga moslashtirdim
        fields = (
            "id",
            "user",
            "title",
            "xp_count",
            "category",
            "meta",
            "proof",
            "created_at",
            "proof_url",
        )

    def get_proof_url(self, obj):
        request = (
            self.context.get("request") if isinstance(self.context, dict) else None
        )
        url = getattr(obj, "proof_url", None) or getattr(obj, "proof", None)
        if callable(url):
            try:
                url = url()
            except Exception:
                url = None
        if url and request and isinstance(url, str) and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url


class MessageSerializer(serializers.ModelSerializer):
    """
    Xabarlar uchun serializer.

    - Frontend POST da `to_id` yoki `to` yuborib yuborsa ham, bu yerda `to_user`ga
      avtomatik çevriladi.
    - Shuningdek `body`, `message`, `content` kelib qolsa, `text`ga map qilinadi.
    """

    # o‘qishda nested user ma’lumot
    from_user = UserSerializer(read_only=True)
    to_user_detail = UserSerializer(source="to_user", read_only=True)

    # yozishda faqat id yuboramiz
    to_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        write_only=True,
    )

    class Meta:
        model = Message
        fields = (
            "id",
            "from_user",
            "to_user",        # write-only (id)
            "to_user_detail", # read-only (full object)
            "text",
            "created_at",
            "read",
        )
        read_only_fields = ("id", "from_user", "created_at", "read")

    def to_internal_value(self, data):
        """
        Kelayotgan requestdagi nomlarni normalize qiladi:
        - to_id / to  -> to_user
        - body / message / content -> text
        """
        # data QueryDict bo‘lishi mumkin, avval copy qilib olamiz
        if hasattr(data, "copy"):
            data = data.copy()
        else:
            data = dict(data)

        # to_user nomini normalize qilish
        if "to_user" not in data:
            for key in ("to_id", "to", "receiver", "toUser"):
                if key in data and data.get(key):
                    data["to_user"] = data.get(key)
                    break

        # text nomini normalize qilish
        if "text" not in data:
            for key in ("body", "message", "msg", "content"):
                if key in data and data.get(key):
                    data["text"] = data.get(key)
                    break

        return super().to_internal_value(data)

    def to_representation(self, instance):
        """
        Frontendga qulay bo‘lishi uchun:
        - from_id
        - to_id
        nomli soddaroq fieldlarni ham qo‘shib yuboramiz.
        """
        rep = super().to_representation(instance)
        rep["from_id"] = instance.from_user_id
        rep["to_id"] = instance.to_user_id
        return rep


class ResumeSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = ("id", "user", "filename", "file", "file_url", "created_at")

    def get_file_url(self, obj):
        request = (
            self.context.get("request") if isinstance(self.context, dict) else None
        )
        if hasattr(obj, "file") and obj.file:
            try:
                url = obj.file.url
                if request and isinstance(url, str) and url.startswith("/"):
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                return getattr(obj, "file", None)
        return None


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    fullname = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.ImageField(required=False, allow_null=True)
