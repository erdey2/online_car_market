from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProfileViewSet, UserRoleViewSet, BuyerUserViewSet, ERPLoginView

router = DefaultRouter()
router.register(r'profiles', ProfileViewSet, basename='profile')
router.register(r'me/roles', UserRoleViewSet, basename='user-roles')
router.register(r'list', BuyerUserViewSet, basename='users-list')

urlpatterns = [
    path('', include(router.urls)),
    path('erp/login/', ERPLoginView.as_view(), name='erp-login'),
]

