from django.urls import path
from rest_framework.routers import DefaultRouter
from online_car_market.payroll.api.views import PayrollRunViewSet, PayslipAPIView, PayslipMeAPIView

router = DefaultRouter()
router.register("payroll-runs", PayrollRunViewSet, basename="payroll-run")


urlpatterns = [
    *router.urls,
    path("payslips/", PayslipAPIView.as_view(), name="payslip"),
    path("payslips/me/", PayslipMeAPIView.as_view(), name="payslip-me"),
]

