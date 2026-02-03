from django.urls import path
from rest_framework.routers import DefaultRouter
from online_car_market.payroll.api.views import (PayrollRunViewSet,
                                                 EmployeeViewSet, PayslipAPIView,
                                                 EmployeeSalaryViewSet, SalaryComponentViewSet,
                                                 OvertimeEmployeeViewSet
                                                 )

router = DefaultRouter()
router.register("employees", EmployeeViewSet, basename="employee")
router.register("payroll-runs", PayrollRunViewSet, basename="payroll-run")
router.register("salary-components", SalaryComponentViewSet, basename="salary-component")
router.register("employee-salaries", EmployeeSalaryViewSet, basename="employee-salary")
router.register("overtime", OvertimeEmployeeViewSet, basename="employee-overtime")

urlpatterns = [
    *router.urls,
    path("payslips/", PayslipAPIView.as_view(), name="payslip"),
]

