from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter
from .views import DealerProfileViewSet, DealerRatingViewSet

router = DefaultRouter()
router.register(r'dealers', DealerProfileViewSet, basename='dealer')

dealers_router = NestedSimpleRouter(router, r'dealers', lookup='dealer')
dealers_router.register(r'ratings', DealerRatingViewSet, basename='dealer-rating')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(dealers_router.urls)),
]
