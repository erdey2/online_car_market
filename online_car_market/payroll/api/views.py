from rest_framework.generics import ListAPIView
from online_car_market.payroll.models import PayrollItem
from online_car_market.payroll.api.serializers import PayslipSerializer, PayrollRunSerializer
from online_car_market.payroll.selectors.payroll_queries import get_latest_payslip
from rest_framework.permissions import IsAuthenticated
from online_car_market.users.permissions.business_permissions import CanViewPayroll, CanRunPayroll, CanApprovePayroll
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view
from online_car_market.payroll.models import PayrollRun
from online_car_market.payroll.services.payroll_runner import run_payroll

@extend_schema_view(
    list=extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="List payroll runs",
        description="Retrieve all payroll runs ordered by creation date (latest first)."
    ),
    retrieve=extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="Retrieve a payroll run",
        description="Get detailed information about a specific payroll run."
    ),
    create=extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="Create a payroll run",
        description=(
            "Create a new payroll run for a specific period. "
            "This does not process payroll until the run action is executed."
        )
    ),
)
class PayrollRunViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post"]
    queryset = PayrollRun.objects.all().order_by("-created_at")
    serializer_class = PayrollRunSerializer
    permission_classes = [IsAuthenticated, CanViewPayroll]

    @extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="Run payroll",
        description=(
            "Execute payroll processing for the selected payroll run. "
            "Calculates salaries, overtime, deductions, and generates payroll items. "
            "Fails if payroll was already processed or required data is missing."
        ),
        responses={
            200: dict,
            400: dict,
        }
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, CanRunPayroll])
    def run(self, request, pk=None):
        payroll_run = self.get_object()

        try:
            result = run_payroll(payroll_run)
        except ValidationError as e:
            # Friendly API error if payroll is posted
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            # Other business rule errors
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"detail": "Payroll processed successfully", "data": result},
            status=status.HTTP_200_OK
        )

    @extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="Approve payroll",
        description=(
            "Approve a processed payroll run. "
            "Once approved, payroll data becomes final and immutable."
        ),
        responses={
            200: dict,
            400: dict,
        }
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, CanApprovePayroll])
    def approve(self, request, pk=None):
        payroll_run = self.get_object()
        payroll_run.approve(by=request.user)
        return Response({"detail": "Payroll approved"})

@extend_schema(
    tags=["Payroll – Payslips"],
    summary="View latest payslip",
    description=(
        "Retrieve the latest payslip for the authenticated employee. "
        "If no payslip exists, an empty response is returned."
    )
)
class PayslipAPIView(ListAPIView):
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # User is not an employee (admin, dealer, HR, finance, etc.)
        if not hasattr(user, "employee_profile"):
            return PayrollItem.objects.none()

        payslip = get_latest_payslip(user.employee_profile)

        if not payslip:
            return PayrollItem.objects.none()

        return PayrollItem.objects.filter(id=payslip.id)






