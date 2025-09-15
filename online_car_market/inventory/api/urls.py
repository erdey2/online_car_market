from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CarViewSet, CarMakeViewSet, CarModelViewSet, FavoriteCarViewSet

router = DefaultRouter()
router.register(r'cars', CarViewSet, basename='cars')
router.register(r'makes', CarMakeViewSet)
router.register(r'models', CarModelViewSet)
router.register(r'car-favorites', FavoriteCarViewSet, basename='favorites')
# router.register(r'car-images', CarImageViewSet, basename='car-images')

urlpatterns = [
    path('', include(router.urls)),
]

