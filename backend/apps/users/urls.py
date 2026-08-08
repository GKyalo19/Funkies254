from django.urls import path

from . import views

urlpatterns = [
    path("me/", views.MeView.as_view(), name="user-me"),
    path("me/avatar/", views.AvatarUploadView.as_view(), name="user-avatar"),
]
