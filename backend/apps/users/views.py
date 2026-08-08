from django.conf import settings
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.supabase_storage import SupabaseStorageError, upload_file

from .authentication import clear_auth_cookies, set_auth_cookies
from .models import User
from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .tokens import password_reset_token


def _issue_tokens_response(user, status_code):
    """Shared by register + login: build the user payload and set cookies."""
    refresh = RefreshToken.for_user(user)
    response = Response({"user": UserSerializer(user).data}, status=status_code)
    set_auth_cookies(response, access_token=refresh.access_token, refresh_token=refresh)
    return response


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — creates the account and logs the user in immediately."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _issue_tokens_response(user, status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /api/auth/login/"""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return _issue_tokens_response(serializer.validated_data["user"], status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/auth/logout/ — blacklisting isn't enabled, so we just clear cookies client-side."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        response = Response({"detail": "Logged out."}, status=status.HTTP_200_OK)
        clear_auth_cookies(response)
        return response


class RefreshView(APIView):
    """
    POST /api/auth/token/refresh/

    Reads the refresh cookie (never sent from JS), issues a fresh access
    (and rotated refresh) token pair, and re-sets both cookies. The frontend
    calls this whenever an API request comes back 401.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE)
        if not raw_refresh:
            return Response({"detail": "No refresh token cookie found."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(raw_refresh)
            new_access = refresh.access_token
        except TokenError:
            response = Response({"detail": "Refresh token is invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
            clear_auth_cookies(response)
            return response

        response = Response({"detail": "Token refreshed."}, status=status.HTTP_200_OK)
        set_auth_cookies(response, access_token=new_access, refresh_token=refresh)
        return response


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/request/

    Always responds with 200 regardless of whether the email exists, so an
    attacker can't use this endpoint to discover which emails are registered.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        user = User.objects.filter(email=email).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = password_reset_token.make_token(user)
            reset_link = f"{settings.FRONTEND_BASE_URL}/pages/reset-password.html?uid={uid}&token={token}"
            send_mail(
                subject="Reset your Funkies254 password",
                message=(
                    f"Hi {user.full_name},\n\n"
                    f"Click the link below to reset your password. This link expires soon.\n\n"
                    f"{reset_link}\n\n"
                    "If you didn't request this, you can safely ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )

        return Response(
            {"detail": "If that email is registered, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """POST /api/auth/password-reset/confirm/ — takes the uid+token from the emailed link."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password reset. You can now log in."}, status=status.HTTP_200_OK)


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/users/me/ — the logged-in user's own profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class AvatarUploadView(APIView):
    """POST /api/users/me/avatar/ — multipart file upload, stored in Supabase Storage."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file_obj = request.FILES.get("avatar")
        if not file_obj:
            return Response({"detail": "No file provided under the 'avatar' field."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            public_url = upload_file(file_obj, folder="users/avatars")
        except SupabaseStorageError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        request.user.avatar_url = public_url
        request.user.save(update_fields=["avatar_url"])
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)
