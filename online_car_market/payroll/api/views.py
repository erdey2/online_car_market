from django.db.models import Prefetch
from rest_framework.generics import ListAPIView, RetrieveAPIView
from online_car_market.payroll.models import PayrollItem, PayrollLine
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

def payslip_queryset():
    return PayrollItem.objects.select_related(
        "employee",
        "employee__user",
        "payroll_run",
    ).prefetch_related(
        Prefetch(
            "lines",
            queryset=PayrollLine.objects.select_related("component"),
        )
    )


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
            "Accessible to dealer, HR staff, accountant staff, and finance staff."
        ),
        responses={200: PayrollRunSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="Retrieve a payroll run",
        description=(
            "Get detailed information about a specific payroll run. "
            "Accessible to dealer, HR staff, accountant staff, and finance staff."
        ),
        responses={200: PayrollRunSerializer},
    ),
    create=extend_schema(
        tags=["Payroll – Payroll Runs"],
        summary="Create a payroll run",
        description=(
            "Create a new payroll run for a specific period. "
            "This creates the run record only; payroll is processed later using the run action. "
            "Accessible to users dealer, hr staff, accountant staff, and finance staff."
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
            "Allowed roles: dealer and HR staff."
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
            "Allowed roles: dealer only."
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
            "Allowed roles: dealer and finance staff."
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
    description="""
List payslips.

### Behavior by role

#### Dealer / HR / Accountant / Finance
Returns **all payslips**, ordered by newest payroll run first.

#### Regular employee
Returns only the authenticated employee's **latest payslip**.

### Permissions
Requires authentication.
""",
    responses={200: PayslipSerializer(many=True)},
)
class PayslipAPIView(ListAPIView):
    """
    GET /api/payroll/payslips/

    - Admin / HR / Accountant / Finance → all payslips
    - Employee → latest own payslip
    """
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Payroll staff can view all payslips
        if user.role == "dealer" or is_staff(
            user,
            ["hr", "accountant", "finance"]
        ):
            return payslip_queryset().order_by("-payroll_run__created_at")

        # Employee can only see own latest payslip
        if not hasattr(user, "employee_profile"):
            return PayrollItem.objects.none()

        payslip = get_latest_payslip(user.employee_profile)

        if not payslip:
            return PayrollItem.objects.none()

        return payslip_queryset().filter(id=payslip.id)

@extend_schema(
    tags=["Payroll – Payslips"],
    summary="Get my latest payslip",
    description="""
Retrieve the authenticated employee's latest payslip.

### Returns
The most recent payslip for the logged-in employee.

### Failure conditions
Returns **404** if:

- User is not an employee
- No payslip exists

### Permissions
Requires authentication.
""",
    responses={
        200: PayslipSerializer,
        404: inline_serializer(
            name="PayslipNotFoundResponse",
            fields={
                "detail": serializers.CharField()
            }
        ),
    },
)
class PayslipMeAPIView(RetrieveAPIView):
    """
    GET /api/payroll/payslips/me/

    Returns latest payslip for authenticated employee.
    """
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user

        if not hasattr(user, "employee_profile"):
            from django.http import Http404
            raise Http404("User is not an employee.")

        payslip = get_latest_payslip(user.employee_profile)

        if not payslip:
            from django.http import Http404
            raise Http404("No payslip found.")

        return payslip_queryset().get(id=payslip.id)






