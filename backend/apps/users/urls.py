"""Routes mounted under /api/."""

from django.urls import path

from apps.users.views import (
    MeView,
    UserListView,
    UserReinstateView,
    UserRoleView,
    UserSuspendView,
)

urlpatterns = [
    path("users/me/", MeView.as_view(), name="user-me"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<uuid:pk>/suspend/", UserSuspendView.as_view(), name="user-suspend"),
    path("users/<uuid:pk>/reinstate/", UserReinstateView.as_view(), name="user-reinstate"),
    path("users/<uuid:pk>/role/", UserRoleView.as_view(), name="user-role"),
]
