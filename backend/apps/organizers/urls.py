from rest_framework.routers import DefaultRouter

from .views import OrganizerViewSet

router = DefaultRouter()
router.register("", OrganizerViewSet, basename="organizer")

urlpatterns = router.urls
