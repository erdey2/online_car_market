from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InspectionViewSet, InspectorViewSet

router = DefaultRouter()
router.register(r'', InspectionViewSet, basename='inspection')
router.register(r"inspectors", InspectorViewSet, basename="inspectors")



urlpatterns = [
    path('', include(router.urls)),
]
