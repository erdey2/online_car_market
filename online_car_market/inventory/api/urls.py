from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CarViewSet, CarImageViewSet

router = DefaultRouter()
router.register(r'cars', CarViewSet, basename='cars')
router.register(r'car-images', CarImageViewSet, basename='car-images')

urlpatterns = [
    path('', include(router.urls)),
]

