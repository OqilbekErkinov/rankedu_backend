# core/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Badge, Message, Resume
import json


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")


class ProfileSerializer(serializers.ModelSerializer):
    """
    Profile uchun serializer.

    - user -> nested (read only)
    - user_id, avatar_url -> computed
    - full_name, university_short, university_full, major -> ODDIY yoziladigan fieldlar
      (endi read-only emas, PATCH/PUT orqali yangilanishi mumkin)
    """

    user = UserSerializer(read_only=True)
    user_id = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        # modeldagi hamma fieldlar + bizning qo‘shimcha fieldlar
        fields = "__all__"
        # faqat mana bular read-only bo‘lsin
        read_only_fields = ("user", "user_id", "avatar_url")

    # ---- helperlar ----
    def get_user_id(self, obj):
        try:
            return obj.user.id
        except Exception:
            return getattr(obj, "user_id", None)

    def get_avatar_url(self, obj):
        """
        avatar fayl bo‘lsa -> .url
        yo‘q bo‘lsa avatar_url/ avatarUrl kabi boshqa attr yoki metani ishlatadi
        """
        request = (
            self.context.get("request") if isinstance(self.context, dict) else None
        )
        url = None

        # 1) modeldagi ImageField
        if hasattr(obj, "avatar") and getattr(obj, "avatar"):
            try:
                url = obj.avatar.url
            except Exception:
                url = getattr(obj, "avatar", None)

        # 2) boshqa attr / meta dan olish
        if not url:
            url = getattr(obj, "avatar_url", None) or getattr(obj, "avatarUrl", None)
            if callable(url):
                try:
                    url = url()
                except Exception:
                    url = None

        # 3) relative bo‘lsa absolute qilamiz
        if url and request and isinstance(url, str) and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url

    def to_representation(self, obj):
        """
        Frontendga qaytishda, agar ba'zi fieldlar bo‘sh bo‘lsa,
        fallback qiymatlarni qo‘shib yuboramiz (masalan full_name).
        Yozish jarayoniga halal bermaydi.
        """
        data = super().to_representation(obj)

        # full_name bo‘sh bo‘lsa user'dan yig‘ib beramiz
        if not data.get("full_name"):
            user = getattr(obj, "user", None)
            if user:
                fn = (getattr(user, "first_name", "") or "").strip()
                ln = (getattr(user, "last_name", "") or "").strip()
                full = f"{fn} {ln}".strip()
                if not full:
                    full = (
                        getattr(user, "username", "")
                        or (getattr(user, "email", "") or "").split("@")[0]
                    )
                data["full_name"] = full

        # agar modelda university_short / full / major fieldlari bo‘sh bo‘lsa,
        # ixtiyoriy meta'dan yoki boshqa attrdan olishga harakat qilamiz (bo‘lsa-bo‘lmasa)
        meta = getattr(obj, "meta", None)
        if isinstance(meta, dict):
            if not data.get("university_short"):
                data["university_short"] = (
                    meta.get("university_short")
                    or meta.get("universityShort")
                    or meta.get("university")
                    or meta.get("school")
                    or ""
                )
            if not data.get("university_full"):
                data["university_full"] = (
                    meta.get("university_full")
                    or meta.get("universityFull")
                    or meta.get("university_name")
                    or meta.get("university")
                    or ""
                )
            if not data.get("major"):
                data["major"] = (
                    meta.get("major")
                    or meta.get("speciality")
                    or meta.get("specialization")
                    or meta.get("field")
                    or meta.get("degree")
                    or ""
                )

        return data


class BadgeSerializer(serializers.ModelSerializer):
    # user – faqat o‘qish uchun, create/update da viewset o‘zi qo‘yadi
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    # Faylni faqat yozishda qabul qilamiz, javobda ko‘rsatmaymiz
    proof = serializers.FileField(
        write_only=True, required=False, allow_null=True
    )

    # Frontend uchun ko‘rinadigan URL
    proof_url = serializers.SerializerMethodField()

    class Meta:
        model = Badge
        fields = (
            "id",
            "user",
            "title",
            "xp_count",
            "category",
            "meta",
            "proof",        # write_only
            "created_at",
            "proof_url",    # read_only URL
        )
        extra_kwargs = {
            "meta": {"required": False, "allow_null": True},
        }

    def get_proof_url(self, obj):
        """
        Faylga havola qaytaramiz:
        - Agar FileField bo‘lsa: .url dan foydalanamiz
        - Agar eski ma'lumotlarda 'proof' maydoni bytes / str bo‘lsa, str() qilamiz
        """
        request = (
            self.context.get("request") if isinstance(self.context, dict) else None
        )

        f = getattr(obj, "proof", None)
        if not f:
            # ehtimol modelda alohida proof_url maydoni bo‘lishi mumkin:
            alt = getattr(obj, "proof_url", None)
            if alt:
                url = str(alt)
            else:
                return None
        else:
            # FileField bo‘lsa
            try:
                if hasattr(f, "url"):
                    url = f.url
                else:
                    url = str(f)
            except Exception:
                url = str(f)

        # Absolyut URL ga aylantirish
        if request and isinstance(url, str) and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url

    def to_representation(self, instance):
        """
        Har ehtimolga qarshi, serializer chiqargan ma'lumot ichida
        bytes / memoryview qolsa, ularni str() ga aylantirib yuboramiz,
        shunda json.dumps(...) UTF-8 decode xatosi bermaydi.
        """
        rep = super().to_representation(instance)
        for key, value in list(rep.items()):
            if isinstance(value, (bytes, bytearray, memoryview)):
                try:
                    rep[key] = value.decode("utf-8", errors="ignore")
                except Exception:
                    rep[key] = str(value)
        return rep



class MessageSerializer(serializers.ModelSerializer):
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
        if hasattr(data, "copy"):
            data = data.copy()
        else:
            data = dict(data)

        if "to_user" not in data:
            for key in ("to_id", "to", "receiver", "toUser"):
                if key in data and data.get(key):
                    data["to_user"] = data.get(key)
                    break

        if "text" not in data:
            for key in ("body", "message", "msg", "content"):
                if key in data and data.get(key):
                    data["text"] = data.get(key)
                    break

        return super().to_internal_value(data)

    def to_representation(self, instance):
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
