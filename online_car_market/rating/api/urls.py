from rest_framework.routers import DefaultRouter
from .views import CarRatingViewSet

router = DefaultRouter()
router.register(r'car-ratings', CarRatingViewSet, basename='car-rating')

urlpatterns = router.urls
