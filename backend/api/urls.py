"""
URL configuration for ecommerce project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import (
    CustomTokenObtainPairView,
    RegisterView,
    ChangePasswordView,
    CurrentUserView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
)
from accounts.views import GoogleAuthUrlView, GoogleCallbackView, GoogleLoginView
from accounts.views import FacebookAuthUrlView, FacebookCallbackView, FacebookLoginView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication endpoints (custom: đăng nhập bằng username hoặc email)
    path('api/auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/registration/', RegisterView.as_view(), name='register'),
    path('api/auth/user/', CurrentUserView.as_view(), name='current_user'),
    path('api/auth/password/change/', ChangePasswordView.as_view(), name='password_change'),
    path('api/auth/password/reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('api/auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Google OAuth endpoints
    path('api/auth/google/url/', GoogleAuthUrlView.as_view(), name='google_auth_url'),
    path('api/auth/google/callback/', GoogleCallbackView.as_view(), name='google_callback'),
    path('api/auth/google/login/', GoogleLoginView.as_view(), name='google_login'),

    # Facebook OAuth endpoints
    path('api/auth/facebook/url/', FacebookAuthUrlView.as_view(), name='facebook_auth_url'),
    path('api/auth/facebook/callback/', FacebookCallbackView.as_view(), name='facebook_callback'),
    path('api/auth/facebook/login/', FacebookLoginView.as_view(), name='facebook_login'),

    # App endpointsc
    path('api/accounts/', include('accounts.urls')),
    path('api/products/', include('products.urls')),
    path('api/cart/', include('cart.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/reviews/', include('reviews.urls')),
    path('api/contact/', include('contact.urls')),
    path('api/core/', include('core.api_urls')),
    path('api/wishlist/', include('wishlist.urls')),
    path('api/payments/', include('payments.urls')),

    # Wallet endpoints
    path('api/wallets/', include('wallets.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
