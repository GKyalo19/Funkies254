"""Routes mounted under /api/auth/."""

from django.urls import path

from apps.users.views import (
    CsrfTokenView,
    LoginView,
    LogoutView,
    RegisterView,
    ResendVerificationView,
    TokenRefreshView,
    VerifyEmailView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path(
        "resend-verification/",
        ResendVerificationView.as_view(),
        name="auth-resend-verification",
    ),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("csrf/", CsrfTokenView.as_view(), name="auth-csrf"),
]
