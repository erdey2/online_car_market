from django.urls import path, include
from django.views.decorators.cache import cache_page
from rest_framework.routers import DefaultRouter
from .views import (CarViewSet, CarMakeViewSet, CarModelViewSet, FavoriteCarViewSet, CarViewViewSet,
                    UserCarsViewSet, PopularCarsViewSet, ContactViewSet, InspectionViewSet)

router = DefaultRouter()
router.register(r'cars', CarViewSet, basename='cars')
router.register(r'makes', CarMakeViewSet)
router.register(r'models', CarModelViewSet)
router.register(r'car-favorites', FavoriteCarViewSet, basename='favorites')
router.register(r'car-views', CarViewViewSet, basename='car-view')
router.register(r'user-cars', UserCarsViewSet, basename='user-car')
router.register(r'popular-cars', PopularCarsViewSet, basename='popular-car')
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'inspections', InspectionViewSet, basename='inspection')
# router.register(r'car-images', CarImageViewSet, basename='car-images')

urlpatterns = [
    path('', include(router.urls)),
]

