"""Authentication and user endpoints (§9)."""

from django.middleware.csrf import get_token
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.enums import ADMIN_ROLES
from apps.common.permissions import IsAdmin
from apps.users import tokens as token_service
from apps.users.models import User
from apps.users.serializers import (
    LoginSerializer,
    RegisterSerializer,
    RoleChangeSerializer,
    UserAdminSerializer,
    UserSerializer,
)
from apps.users.services import change_user_role, set_user_active


def _authenticated_response(request, user, *, status_code=status.HTTP_200_OK, detail=None):
    """Serialise the user, attach auth cookies and seed the CSRF cookie."""
    payload = {
        "user": UserSerializer(user, context={"request": request}).data,
        # Lets a cookie-authenticated frontend send X-CSRFToken on its next write.
        "csrf_token": get_token(request),
    }
    if detail:
        payload["detail"] = detail

    response = Response(payload, status=status_code)
    refresh, access = token_service.issue_tokens(user)
    return token_service.set_auth_cookies(response, access, refresh)


class CsrfTokenView(APIView):
    """Hands the frontend a CSRF token/cookie before its first write request."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class RegisterView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _authenticated_response(
            request,
            user,
            status_code=status.HTTP_201_CREATED,
            detail="Account created successfully.",
        )


class LoginView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return _authenticated_response(
            request, serializer.validated_data["user"], detail="Login successful."
        )


class TokenRefreshView(APIView):
    """Rotates the refresh token and re-issues both cookies."""

    permission_classes = (AllowAny,)
    authentication_classes = ()

    def post(self, request):
        raw_refresh = token_service.read_refresh_token(request)
        if not raw_refresh:
            return Response(
                {"detail": "No refresh token was provided.", "code": "no_refresh_token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            refresh = RefreshToken(raw_refresh)
            access = refresh.access_token
        except TokenError:
            response = Response(
                {"detail": "Refresh token is invalid or expired.", "code": "invalid_refresh_token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            return token_service.clear_auth_cookies(response)

        rotated = None
        if refresh.token_type == "refresh":
            token_service.blacklist_refresh_token(raw_refresh)
            user = User.objects.filter(pk=refresh.payload.get("user_id")).first()
            if user is None or not user.is_active:
                response = Response(
                    {"detail": "Account is no longer active.", "code": "inactive_account"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                return token_service.clear_auth_cookies(response)
            rotated, access = token_service.issue_tokens(user)

        response = Response({"detail": "Token refreshed."})
        return token_service.set_auth_cookies(response, access, rotated)


class LogoutView(APIView):
    """Clears the cookies and blacklists the refresh token."""

    permission_classes = (AllowAny,)

    def post(self, request):
        token_service.blacklist_refresh_token(token_service.read_refresh_token(request))
        response = Response({"detail": "Logged out."})
        return token_service.clear_auth_cookies(response)


class MeView(generics.RetrieveUpdateAPIView):
    """GET/PATCH the authenticated user's own profile."""

    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    http_method_names = ("get", "patch", "head", "options")

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    """Administrative account listing (§14)."""

    serializer_class = UserAdminSerializer
    permission_classes = (IsAdmin,)
    queryset = User.objects.select_related("institution").all()
    filterset_fields = ("role", "is_active", "institution")
    search_fields = ("email", "name")
    ordering_fields = ("created_at", "email", "name", "role")
    ordering = ("-created_at",)


class UserSuspendView(APIView):
    """Suspend an account so future authentication is rejected (§10.5)."""

    permission_classes = (IsAdmin,)

    def post(self, request, pk):
        user = generics.get_object_or_404(User, pk=pk)
        self._guard(request, user)
        set_user_active(actor=request.user, user=user, is_active=False)
        return Response(UserAdminSerializer(user).data)

    def _guard(self, request, user):
        from rest_framework.exceptions import PermissionDenied

        if user.id == request.user.id:
            raise PermissionDenied("You cannot suspend your own account.")
        if user.role in ADMIN_ROLES and not request.user.is_super_admin:
            raise PermissionDenied(
                "Only a super administrator may suspend an administrator account."
            )


class UserReinstateView(APIView):
    permission_classes = (IsAdmin,)

    def post(self, request, pk):
        user = generics.get_object_or_404(User, pk=pk)
        set_user_active(actor=request.user, user=user, is_active=True)
        return Response(UserAdminSerializer(user).data)


class UserRoleView(APIView):
    """Change an account's application role (§13 promoted_user)."""

    permission_classes = (IsAdmin,)

    def post(self, request, pk):
        from rest_framework.exceptions import PermissionDenied

        user = generics.get_object_or_404(User, pk=pk)
        serializer = RoleChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        if user.role in ADMIN_ROLES and not request.user.is_super_admin:
            raise PermissionDenied(
                "Only a super administrator may change an administrator's role."
            )
        if user.id == request.user.id:
            raise PermissionDenied("You cannot change your own role.")

        change_user_role(actor=request.user, user=user, role=serializer.validated_data["role"])
        return Response(UserAdminSerializer(user).data)
