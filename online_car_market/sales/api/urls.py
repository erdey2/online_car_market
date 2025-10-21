from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, LeadViewSet

router = DefaultRouter()
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'', SaleViewSet, basename='sale')

urlpatterns = [
    path('', include(router.urls)),
]
