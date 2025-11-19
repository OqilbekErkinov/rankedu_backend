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
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import models as djmodels
import uuid

# helper: create tokens
def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh)
    }

# Register view: returns user + tokens
class RegisterView(views.APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        data = request.data
        email = (data.get("email") or "").strip().lower()
        password = data.get("password")
        fullname = data.get("fullname") or ""
        phone = data.get("phone") or ""
        avatar = data.get("avatar")  # file input or avatarDataUrl

        if not email or not password:
            return Response({"detail": "email and password required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email__iexact=email).exists():
            return Response({"email": ["This email already registered."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(password)
        except ValidationError as e:
            return Response({"password": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)

        username = email.split("@")[0]
        user = User.objects.create_user(username=username, email=email, password=password)
        p = user.profile
        p.full_name = fullname
        p.phone = phone
        # if avatar file provided via multipart
        if avatar and hasattr(avatar, "name"):
            p.avatar = avatar
        p.save()

        # produce tokens and return
        tokens = tokens_for_user(user)
        user_ser = UserSerializer(user)
        profile_ser = ProfileSerializer(user.profile, context={"request": request})
        return Response({"user": user_ser.data, "profile": profile_ser.data, **tokens}, status=status.HTTP_201_CREATED)

# Login view by email -> returns tokens + user
class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password")

        if not email or not password:
            return Response({"detail":"email and password required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({"detail":"No active account found with the given credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            return Response({"detail":"No active account found with the given credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({"detail":"User inactive"}, status=status.HTTP_403_FORBIDDEN)

        tokens = tokens_for_user(user)
        user_ser = UserSerializer(user)
        profile_ser = ProfileSerializer(user.profile, context={"request": request})
        return Response({"user": user_ser.data, "profile": profile_ser.data, **tokens})

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
            # Accept numeric user id, or UUID string, or user id provided as string
            # Try int -> assume numeric; else try UUID -> else use raw string
            try:
                uid = int(user_id)
                qs = qs.filter(user__id=uid)
            except (ValueError, TypeError):
                # try uuid
                try:
                    uid = uuid.UUID(user_id)
                    qs = qs.filter(user__id=str(uid))
                except Exception:
                    # fallback: filter by user__username or nothing
                    qs = qs.filter(user__id=user_id)
        return qs

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = ProfileSerializer(request.user.profile, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["put","patch"], permission_classes=[IsAuthenticated])
    def update_me(self, request):
        p = request.user.profile
        serializer = ProfileSerializer(p, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Messages
class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(djmodels.Q(to_user=user) | djmodels.Q(from_user=user)).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(from_user=self.request.user)

# Badges read-only
class BadgeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BadgeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Badge.objects.all().order_by("-created_at")
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

# Resume upload
class ResumeUploadView(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail":"file required"}, status=status.HTTP_400_BAD_REQUEST)
        resume = Resume.objects.create(user=request.user, file=f, filename=f.name)
        ser = ResumeSerializer(resume, context={"request": request})
        return Response(ser.data, status=status.HTTP_201_CREATED)
