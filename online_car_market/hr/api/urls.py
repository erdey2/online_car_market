from rest_framework.routers import DefaultRouter
from .views import (EmployeeViewSet, ContractViewSet, AttendanceViewSet, LeaveViewSet, SalaryComponentViewSet,
                    EmployeeSalaryViewSet, OvertimeEmployeeViewSet)

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'contracts', ContractViewSet, basename='contract')
router.register(r'attendances', AttendanceViewSet, basename='attendance')
router.register(r'leaves', LeaveViewSet, basename='leave')
router.register("salary-components", SalaryComponentViewSet, basename="salary-component")
router.register("employee-salaries", EmployeeSalaryViewSet, basename="employee-salary")
router.register("overtime", OvertimeEmployeeViewSet, basename="employee-overtime")

urlpatterns = router.urls
