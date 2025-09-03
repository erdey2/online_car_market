from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProfileViewSet, UserRoleViewSet

router = DefaultRouter()
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'roles', UserRoleViewSet, basename='role')

urlpatterns = [
    path('', include(router.urls)),
]

