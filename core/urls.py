# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, LoginView, MeView, ProfileViewSet, MessageViewSet, BadgeViewSet, ResumeUploadView

router = DefaultRouter()
router.register(r'profiles', ProfileViewSet, basename='profiles')
router.register(r'messages', MessageViewSet, basename='messages')
router.register(r'badges', BadgeViewSet, basename='badges')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('resume/upload/', ResumeUploadView.as_view(), name='resume-upload'),
    path('', include(router.urls)),
]
