from rest_framework import views, viewsets, status, permissions
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Profile, Badge, Message, Resume
from .serializers import (
    UserSerializer,
    ProfileSerializer,
    BadgeSerializer,
    MessageSerializer,
    ResumeSerializer,
    RegisterSerializer,
)
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.files.base import ContentFile
from django.db.models import Q
import base64, uuid


# helper: create tokens
def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


# Register view: returns user + tokens
class RegisterView(views.APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        data = request.data
        email = (data.get("email") or "").strip().lower()
        password = data.get("password")
        fullname = data.get("fullname") or ""
        phone = data.get("phone") or ""
        avatar_file = request.FILES.get("avatar")
        avatar_dataurl = (
            data.get("avatarDataUrl") or data.get("avatar_data_url") or None
        )

        if not email or not password:
            return Response(
                {"detail": "email and password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"email": ["This email already registered."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(password)
        except ValidationError as e:
            return Response(
                {"password": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST
            )

        username = email.split("@")[0]
        user = User.objects.create_user(
            username=username, email=email, password=password
        )
        p, created = Profile.objects.get_or_create(
            user=user, defaults={"full_name": fullname, "phone": phone}
        )
        p.full_name = fullname or p.full_name
        p.phone = phone or p.phone

        if avatar_file and hasattr(avatar_file, "name"):
            p.avatar = avatar_file
        else:
            if avatar_dataurl:
                try:
                    header, base64data = (
                        avatar_dataurl.split(",", 1)
                        if "," in avatar_dataurl
                        else ("", avatar_dataurl)
                    )
                    if header and "/" in header:
                        fmt = header.split(";")[0].split("/")[1]
                    else:
                        fmt = "png"
                    filename = f"avatar_{uuid.uuid4().hex}.{fmt}"
                    data_file = ContentFile(
                        base64.b64decode(base64data), name=filename
                    )
                    p.avatar.save(filename, data_file, save=False)
                except Exception:
                    # avatar bilan muammo bo'lsa, foydalanuvchini baribir yaratamiz
                    pass
        p.save()

        tokens = tokens_for_user(user)
        user_ser = UserSerializer(user)
        profile_ser = ProfileSerializer(p, context={"request": request})
        return Response(
            {
                "user": user_ser.data,
                "profile": profile_ser.data,
                **tokens,
            },
            status=status.HTTP_201_CREATED,
        )


# Login view by email -> returns tokens + user
class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "email and password required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "No active account found with the given credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {"detail": "No active account found with the given credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "User inactive"}, status=status.HTTP_403_FORBIDDEN
            )

        tokens = tokens_for_user(user)
        user_ser = UserSerializer(user)
        profile_ser = ProfileSerializer(user.profile, context={"request": request})
        return Response(
            {
                "user": user_ser.data,
                "profile": profile_ser.data,
                **tokens,
            }
        )


# me endpoint
class MeView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ser = UserSerializer(user)
        prof = ProfileSerializer(user.profile, context={"request": request})
        return Response({"user": ser.data, "profile": prof.data})


# Profile ViewSet
class ProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Profile.objects.select_related("user").all()
        user_id = self.request.query_params.get("user_id")
        if user_id:
            try:
                uid = int(user_id)
                qs = qs.filter(user__id=uid)
            except (ValueError, TypeError):
                try:
                    uid = uuid.UUID(user_id)
                    qs = qs.filter(user__id=str(uid))
                except Exception:
                    qs = qs.filter(user__id=user_id)
        return qs

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = ProfileSerializer(
            request.user.profile, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["put", "patch"],
        permission_classes=[IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def update_me(self, request):
        """
        Profilni yangilash (frontenddagi /profiles/update_me/ ga mos).
        - full_name, university_short, university_full, major, xp, avatar yoziladi
        - remove_avatar=true bo‘lsa avatar o‘chirib tashlanadi
        """
        profile = request.user.profile
        data = request.data.copy()

        # frontenddan kelyapti: { remove_avatar: true }
        remove_avatar = data.pop("remove_avatar", None)

        serializer = ProfileSerializer(
            profile, data=data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        profile = serializer.save()

        # agar remove_avatar flag bo‘lsa – faylni o‘chirib yuboramiz
        flag = False
        if isinstance(remove_avatar, str):
            flag = remove_avatar.lower() in ["1", "true", "yes", "on"]
        elif isinstance(remove_avatar, bool):
            flag = remove_avatar

        if flag:
            if getattr(profile, "avatar", None):
                profile.avatar.delete(save=False)
            profile.avatar = None
            profile.save(update_fields=["avatar"])

        # yangilangan profilni qaytaramiz
        out = ProfileSerializer(profile, context={"request": request})
        return Response(out.data)



# Messages
class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Faqat shu userga tegishli xabarlar.
        Agar ?with=<user_id> bo‘lsa – aniq dialog bo‘yicha filter.
        Agar ?unread=1 bo‘lsa – faqat o‘qilmaganlar.
        """
        user = self.request.user
        qs = Message.objects.filter(
            Q(to_user=user) | Q(from_user=user)
        )

        other_id = self.request.query_params.get("with")
        if other_id:
            qs = qs.filter(
                Q(to_user_id=other_id, from_user=user)
                | Q(from_user_id=other_id, to_user=user)
            )

        unread_only = self.request.query_params.get("unread")
        if str(unread_only) in ("1", "true", "True"):
            qs = qs.filter(to_user=user, read=False)

        return qs.order_by("created_at")

    def perform_create(self, serializer):
        # from_user = request.user
        serializer.save(from_user=self.request.user)

    @action(detail=False, methods=["post"], url_path="mark-read")
    def mark_read(self, request):
        """
        POST /api/messages/mark-read/
        body: { "with": <user_id> }

        Shu user bilan bo‘lgan dialogdagi
        "menga kelgan" o‘qilmagan xabarlarni read=True qiladi.
        """
        other_id = request.data.get("with")
        if not other_id:
            return Response(
                {"detail": '"with" field is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            other_id = int(other_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": '"with" must be integer user id'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        qs = Message.objects.filter(
            to_user=user,
            from_user_id=other_id,
            read=False,
        )
        updated_count = qs.update(read=True)
        return Response({"updated": updated_count})

# Badges: allow create/update/delete
class BadgeViewSet(viewsets.ModelViewSet):
    serializer_class = BadgeSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = Badge.objects.all().order_by("-created_at")
        user_id = self.request.query_params.get("user_id")
        if user_id:
            try:
                uid = int(user_id)
                qs = qs.filter(user__id=uid)
            except (ValueError, TypeError):
                qs = qs.filter(user__id=user_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)



# Resume upload
class ResumeUploadView(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response(
                {"detail": "file required"}, status=status.HTTP_400_BAD_REQUEST
            )
        resume = Resume.objects.create(user=request.user, file=f, filename=f.name)
        ser = ResumeSerializer(resume, context={"request": request})
        return Response(ser.data, status=status.HTTP_201_CREATED)
