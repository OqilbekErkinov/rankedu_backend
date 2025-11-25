from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, LoginView, MeView, ProfileViewSet, MessageViewSet, BadgeViewSet, ResumeUploadView

router = DefaultRouter()
router.register(r"profiles", ProfileViewSet, basename="profile")
router.register(r"messages", MessageViewSet, basename="message")
router.register(r"badges", BadgeViewSet, basename="badge")
# you may want to register resumes if you need list endpoint; here we provide upload view separately

urlpatterns = [
    path("", include(router.urls)),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("resumes/upload/", ResumeUploadView.as_view(), name="resume-upload"),
]
