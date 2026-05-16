from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    BirthdayEmailPreviewView,
    BirthdayEmailTemplateAdminView,
    ProfileViewSet,
    RegisterView,
    ChangePasswordView,
    CurrentUserView,
    PasswordResetRequestView,
)

router = DefaultRouter()
router.register(r'profiles', ProfileViewSet, basename='profile')

urlpatterns = [
    path(
        "birthday-email-template/",
        BirthdayEmailTemplateAdminView.as_view(),
        name="birthday_email_template",
    ),
    path(
        "birthday-email-template/preview/",
        BirthdayEmailPreviewView.as_view(),
        name="birthday_email_preview",
    ),
    # JWT Authentication
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Registration
    path('auth/registration/', RegisterView.as_view(), name='register'),

    # User info
    path('auth/user/', CurrentUserView.as_view(), name='current_user'),

    # Password management
    path('auth/password/change/', ChangePasswordView.as_view(), name='password_change'),
    path('auth/password/reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
]

urlpatterns += router.urls
