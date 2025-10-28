from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet, ContractViewSet, AttendanceViewSet, LeaveViewSet

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'contracts', ContractViewSet, basename='contract')
router.register(r'attendances', AttendanceViewSet, basename='attendance')
router.register(r'leaves', LeaveViewSet, basename='leave')

urlpatterns = router.urls
