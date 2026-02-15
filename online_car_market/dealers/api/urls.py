from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import ( DealerRatingViewSet, ProfileViewSet, DealerStaffViewSet,
                     DealerApplicationView, AdminDealerViewSet)

router = SimpleRouter()
router.register(r'staff', DealerStaffViewSet, basename='dealer-staff')
router.register(r'ratings', DealerRatingViewSet, basename='dealer-rating')
router.register(r'profile', ProfileViewSet, basename='dealer-profile')

admin_router = SimpleRouter()
admin_router.register(r'dealers', AdminDealerViewSet, basename='admin-dealers')

urlpatterns = [
    path('', include(router.urls)),
    path('application/', DealerApplicationView.as_view(), name="dealer-application"),
    path('admin/', include(admin_router.urls)),
]
