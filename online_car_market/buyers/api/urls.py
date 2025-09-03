from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoleUpgradeViewSet

router = DefaultRouter()
router.register(r'upgrades', RoleUpgradeViewSet, basename='upgrade')

urlpatterns = [
    path('', include(router.urls)),
]
