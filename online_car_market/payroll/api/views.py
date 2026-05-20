from rest_framework.generics import ListAPIView
from online_car_market.payroll.models import PayrollItem
from online_car_market.payroll.api.serializers import PayslipSerializer, PayrollRunSerializer
from online_car_market.payroll.selectors.payroll_queries import get_latest_payslip
from rest_framework.permissions import IsAuthenticated
from online_car_market.users.permissions.business_permissions import (
    CanViewPayroll, CanRunPayroll, CanApprovePayroll, CanPostPayroll, is_staff)
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from online_car_market.payroll.models import PayrollRun
from online_car_market.payroll.services.payroll_runner import run_payroll

PayrollActionResponse = inline_serializer(
    name="PayrollActionResponse",
    fields={
        "detail": serializers.CharField(),
    },
)

@extend_schema_view(
    list=extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="List payroll runs",
        description=(
            "Retrieve all payroll runs ordered by creation date (latest first). "
            "Accessible to admin, HR staff, accountant staff, and finance staff."
        ),
        responses={200: PayrollRunSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="Retrieve a payroll run",
        description=(
            "Get detailed information about a specific payroll run. "
            "Accessible to admin, HR staff, accountant staff, and finance staff."
        ),
        responses={200: PayrollRunSerializer},
    ),
    create=extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="Create a payroll run",
        description=(
            "Create a new payroll run for a specific period. "
            "This creates the run record only; payroll is processed later using the run action. "
            "Accessible to users admin, hr staff, accountant staff, and finance staff."
        ),
        request=PayrollRunSerializer,
        responses={201: PayrollRunSerializer},
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
            "Fails if payroll was already processed or required data is missing. "
            "Allowed roles: admin and HR staff."
        ),
        responses={
            200: PayrollActionResponse,
            400: PayrollActionResponse,
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
            "Once approved, payroll data becomes final and immutable. "
            "Allowed roles: admin only."
        ),
        responses={
            200: PayrollActionResponse,
            400: PayrollActionResponse,
        }
    )
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, CanApprovePayroll])
    def approve(self, request, pk=None):
        payroll_run = self.get_object()
        try:
            payroll_run.approve(by=request.user)
        except (ValidationError, ValueError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Payroll approved"})

    @extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="Post payroll",
        description=(
            "Post an approved payroll run. "
            "This is the final workflow step and makes the payroll immutable. "
            "Allowed roles: admin and finance staff."
        ),
        responses={
            200: PayrollActionResponse,
            400: PayrollActionResponse,
        }
    )
    @action(detail=True, methods=["post"], url_path="post", permission_classes=[IsAuthenticated, CanPostPayroll])
    def post_payroll(self, request, pk=None):
        payroll_run = self.get_object()

        try:
            payroll_run.post(by=request.user)
        except (ValidationError, ValueError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Payroll posted"})

@extend_schema(
    tags=["Payroll – Payslips"],
    summary="List payslips / get my latest payslip",
    description=(
        "List payslips.\n\n"
        "- If the authenticated user is admin, HR staff, accountant or finance staff, "
        "this endpoint returns all payslips (paginated if you have pagination).\n\n"
        "- Otherwise (regular employee) it returns only the employee's latest payslip."
    ),
    responses={200: PayslipSerializer(many=True)},
)
class PayslipAPIView(ListAPIView):
    """
    GET /api/payroll/payslips/:
     - Admin/HR/Accountant/Finance => returns all payslips.
     - Employee => returns that employee's latest payslip (same behavior as before).
    """
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin or payroll ops staff should see all payslips
        if user.is_authenticated and (user.role == "admin" or is_staff(user, ["hr", "accountant", "finance"])):
            # use select_related to reduce DB hits
            return PayrollItem.objects.select_related("employee", "employee__user").all().order_by("-created_at")

        # Non-staff: only employees can access their own latest payslip
        if not hasattr(user, "employee_profile"):
            return PayrollItem.objects.none()

        payslip = get_latest_payslip(user.employee_profile)
        if not payslip:
            return PayrollItem.objects.none()

        return PayrollItem.objects.filter(id=payslip.id)

@extend_schema(
    tags=["Payroll – Payslips"],
    summary="Get my latest payslip",
    description=(
        "Retrieve the authenticated employee's latest payslip. "
        "Returns 404 if the authenticated user is not an employee or if no payslip exists."
    ),
    responses={
        200: PayslipSerializer,
        404: inline_serializer(
            name="PayslipNotFoundResponse",
            fields={"detail": serializers.CharField()}
        ),
    },
)
class PayslipMeAPIView(ListAPIView):
    """
    GET /api/payroll/payslips/me/:
      - Returns the latest payslip for the authenticated employee.
      - This endpoint is a convenience path for clients that want just 'my' payslip.
    """
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if not hasattr(user, "employee_profile"):
            return PayrollItem.objects.none()

        payslip = get_latest_payslip(user.employee_profile)
        if not payslip:
            return PayrollItem.objects.none()

        return PayrollItem.objects.filter(id=payslip.id)






