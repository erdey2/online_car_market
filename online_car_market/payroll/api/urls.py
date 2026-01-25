from rest_framework.routers import DefaultRouter
from online_car_market.payroll.api.views import PayrollRunViewSet, PayslipViewSet

router = DefaultRouter()
router.register("payroll-runs", PayrollRunViewSet, basename="payroll-run")
router.register("payslips", PayslipViewSet, basename="payslip")

urlpatterns = router.urls
