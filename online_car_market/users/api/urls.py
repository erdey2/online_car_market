from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (ProfileViewSet, UserRoleViewSet, BuyerUserViewSet, ERPLoginView,
                    AdminLoginView, AuthViewSet, MeView)

router = DefaultRouter()
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'me/roles', UserRoleViewSet, basename='user-roles')
router.register(r'list', BuyerUserViewSet, basename='users-list')
router.register(r'auth', AuthViewSet, basename='auth')

urlpatterns = [
    path('', include(router.urls)),
    path("me/", MeView.as_view(), name="user-me"),
    path('erp/login/', ERPLoginView.as_view(), name='erp-login'),
    path("admin/login/", AdminLoginView.as_view(), name="admin-login"),
]

