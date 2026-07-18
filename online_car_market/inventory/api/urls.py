from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (CarViewSet, CarMakeViewSet, CarModelViewSet, FavoriteCarViewSet, CarViewViewSet,
                    UserCarsViewSet, PopularCarsViewSet, ContactViewSet, CarVerificationViewSet,
                    CarImageViewSet, CarMakeRequestViewSet, CarModelRequestViewSet)

router = DefaultRouter()

# cars
router.register(r'cars', CarViewSet, basename='cars')

# Master Data (Admin Managed)
router.register(r'makes', CarMakeViewSet)
router.register(r'models', CarModelViewSet, basename="car-model")

# Make/model requests (seller/broker request, admin approve)
router.register(r'make-requests', CarMakeRequestViewSet, basename='car-make-requests')
router.register(r'model-requests', CarModelRequestViewSet, basename='car-model-requests')

# verification
router.register(r'car-verifications', CarVerificationViewSet, basename="car-verifications")

# view/favorites
router.register(r'car-favorites', FavoriteCarViewSet, basename='favorites')
router.register(r'car-views', CarViewViewSet, basename='car-view')

router.register(r'user-cars', UserCarsViewSet, basename='user-car')
router.register(r'popular-cars', PopularCarsViewSet, basename='popular-car')
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'car-images', CarImageViewSet, basename='car-images')

urlpatterns = [
    path('', include(router.urls)),
]

