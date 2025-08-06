from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DealerProfileViewSet  # example view

router = DefaultRouter()
router.register(r'dealers', DealerProfileViewSet, basename='dealer')

urlpatterns = [
    path('', include(router.urls)),
]
