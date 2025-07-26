from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BuyerViewSet  # example view

router = DefaultRouter()
router.register(r'buyers', BuyerViewSet, basename='buyer')

urlpatterns = [
    path('', include(router.urls)),
]
