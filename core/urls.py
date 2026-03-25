from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, MeView, ProfileViewSet, MessageViewSet,
    BadgeViewSet, ResumeUploadView, FacultyViewSet, MajorViewSet,
    SocialAchievementViewSet, generate_ranking_view, ScholarshipViewSet,
    ApplicationCreateView, AnnouncementListAPIView, AnnouncementViewUpdateAPIView)

router = DefaultRouter()
router.register(r"profiles", ProfileViewSet, basename="profile")
router.register(r"messages", MessageViewSet, basename="message")
router.register(r"badges", BadgeViewSet, basename="badges")
router.register(r'faculties', FacultyViewSet, basename="faculty")
router.register(r'majors', MajorViewSet, basename="major")
router.register(r'social-achievements', SocialAchievementViewSet, basename='socialachievement')
router.register("scholarships", ScholarshipViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("resumes/upload/", ResumeUploadView.as_view(), name="resume-upload"),
    path("admin/generate-ranking/<int:year_id>/", generate_ranking_view),
    path("applications/", ApplicationCreateView.as_view()),
    path('announcements/', AnnouncementListAPIView.as_view()),
    path('announcements/<int:pk>/view/', AnnouncementViewUpdateAPIView.as_view()),
]
