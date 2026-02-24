import logging
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes

from ..models import Employee, Contract, Attendance, Leave, SalaryComponent, EmployeeSalary, OvertimeEntry
from .serializers import (EmployeeSerializer, ContractSerializer, AttendanceSerializer,
                          LeaveSerializer, SignedUploadSerializer, FinalUploadSerializer,
                          SalaryComponentSerializer, OvertimeSerializer, EmployeeSalarySerializer
                          )
from rest_framework import viewsets
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rolepermissions.checkers import has_role
from online_car_market.users.permissions.drf_permissions import IsHR, IsDealerOrHR, IsFinance
from online_car_market.users.permissions.business_permissions import IsHRorDealer
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiResponse, OpenApiParameter
from ..services.contract_service import ContractService
from ..services.leave_service import LeaveService
from ..services.attendance_service import AttendanceService

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="List all employees",
        description="Retrieve all registered employees, including position, department, and hiring date.",
    ),
    retrieve=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Retrieve employee details",
        description="Fetch detailed information about a specific employee by ID.",
    ),
    create=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Add a new employee",
        description="Dealers or HR can create new employees. `created_by` is automatically tracked.",
    ),
    update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Update employee information",
        description="Modify existing employee details.",
    ),
    partial_update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Partially update employee information",
    ),
    destroy=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Delete employee record",
    ),
)
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHRorDealer]

    def get_queryset(self):
        """
        Optional: Dealers see only employees they created, HR see all.
        """
        user = self.request.user
        if has_role(user, ["dealer"]):
            return Employee.objects.filter(created_by=user)
        return Employee.objects.all()

@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="List all contracts",
        description="Returns a list of all contracts accessible to the HR user.",
    ),
    retrieve=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Retrieve a specific contract",
        description="Fetch a single contract by its ID, including employee details and current status.",
    ),
    create=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Create a new contract",
        description="Allows HR to create a new contract in draft status.",
    ),
    update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Update contract",
        description="Allows HR to update an existing contract as long as it is still in draft stage.",
    ),
    partial_update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Partially update contract",
        description="Allows HR to modify specific fields of a draft contract.",
    ),
    destroy=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Delete contract",
        description="Allows HR to delete a draft contract.",
    ),
    send_to_employee=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Send draft contract to employee",
        description=(
            "Generates a PDF, updates status to `sent_to_employee`, "
            "and emails the employee a download link."
        ),
        request=None,
        responses={200: OpenApiResponse(description="Contract sent to employee.")}
    ),
    upload_signed=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Upload signed contract from employee",
        description=(
            "Employee uploads the signed contract. "
            "Requires file field: `signed_document`."
        ),
        request=SignedUploadSerializer,
        responses={200: OpenApiResponse(description="Signed document received.")}
    ),

    finalize=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Finalize contract and make it active",
        description=(
            "HR uploads the final stamped PDF. "
            "Requires file field: `final_document`."
        ),
        request=FinalUploadSerializer,
        responses={200: OpenApiResponse(description="Contract is now active.")}
    ),
)
class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.select_related('employee__user__profile').all()
    serializer_class = ContractSerializer
    permission_classes = [IsHRorDealer]

    @action(detail=True, methods=['post'])
    def send_to_employee(self, request, pk=None):
        contract = self.get_object()
        try:
            pdf_url = ContractService.send_to_employee(contract)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"detail": "Contract sent!", "pdf_url": pdf_url})

    @action(detail=True, methods=['post'])
    def upload_signed(self, request, pk=None):
        contract = self.get_object()
        file = request.FILES.get('signed_document')
        if not file:
            return Response({"detail": "File required"}, status=400)

        try:
            file_url = ContractService.upload_signed(contract, file)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"detail": "Signed document uploaded", "url": file_url})

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        contract = self.get_object()
        file = request.FILES.get('final_document')
        if not file:
            return Response({"detail": "Final document required"}, status=400)

        try:
            final_url = ContractService.finalize(contract, file, request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)

        return Response({"detail": "Contract is now ACTIVE", "final_pdf": final_url})

@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="List all attendance records",
        description="View attendance history of employees including check-in/check-out times and attendance status.",
    ),
    create=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Record attendance",
        description="Mark attendance for an employee on a specific date with check-in and check-out times.",
    ),
    retrieve=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Retrieve attendance record",
        description="Get detailed attendance information for a specific employee and date.",
    ),
    update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Update attendance record",
        description="Modify an existing attendance entry for corrections or updates.",
    ),
    partial_update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Partially update attendance record",
        description="Update specific fields in an attendance entry, such as check-out time or status.",
    ),
    destroy=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Delete attendance record",
        description="Remove an attendance record permanently from the system.",
    ),
)
class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsHR]

    @extend_schema(
        tags=["Dealers - Human Resource Management"],
        parameters=[
            OpenApiParameter(
                name='year',
                type=OpenApiTypes.INT,
                description='Year to filter analytics (optional, defaults to current year)',
                required=False
            ),
            OpenApiParameter(
                name='month',
                type=OpenApiTypes.INT,
                description='Month to filter analytics (optional, defaults to current month)',
                required=False
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "total_working_hours": {"type": "number", "example": 160},
                    "average_daily_hours": {"type": "number", "example": 8},
                    "employee_count": {"type": "integer", "example": 25},
                },
                "description": "Monthly attendance analytics summary"
            },
            400: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string", "example": "Invalid year or month"}
                }
            }
        },
        description="Get monthly working hours analytics for all employees"
    )
    @action(detail=False, methods=['get'], url_path='payroll-analytics')
    def payroll_analytics(self, request):
        # Safely get the employee profile
        employee = getattr(request.user, 'employee_profile', None)
        if not employee:
            return Response({"detail": "Employee profile not found."}, status=404)

        year = request.query_params.get('year')
        month = request.query_params.get('month')

        from django.utils import timezone
        now = timezone.now()

        try:
            year = int(year) if year else now.year
            month = int(month) if month else now.month
        except ValueError:
            return Response({"detail": "Invalid year or month"}, status=400)

        result = AttendanceService.monthly_employee_payroll(year, month, employee)
        return Response(result)

# leave viewset
@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="List leave requests",
        description="HR can see all leave requests. Employees see only their own.",
    ),
    retrieve=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Retrieve leave details",
    ),
    create=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Request leave",
        description="Employees can request leave. Status defaults to pending.",
    ),
    update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Update leave request (HR)",
    ),
    partial_update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Partially update leave request (HR)",
    ),
    destroy=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Delete leave request (HR only)",
    ),
)
class LeaveViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Leave.objects.select_related("employee__user", "approved_by")

        if has_role(user, 'hr'):
            return qs
        return qs.filter(employee__user=user)

    def get_permissions(self):
        if self.action in ['approve', 'reject', 'destroy']:
            return [IsHR()]
        return [IsAuthenticated()]

    # Employee: my leaves
    @extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="List my leave requests",
        description="Authenticated employees retrieve only their own leave requests.",
        responses={200: LeaveSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='me', permission_classes=[IsAuthenticated])
    def my_leaves(self, request):
        leaves = self.get_queryset()
        serializer = self.get_serializer(leaves, many=True)
        return Response(serializer.data)

    # HR: approve leave
    @extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Approve leave request",
        description="""Approve a pending leave request.""",
        request=None,
        responses={
            200: OpenApiResponse(description="Leave approved successfully"),
            400: OpenApiResponse(description="Leave is not pending"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Leave not found"),
        },
    )
    @action(detail=True, methods=['post'], permission_classes=[IsHR])
    def approve(self, request, pk=None):
        leave = self.get_object()
        try:
            LeaveService.approve_leave(leave, request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"status": "approved"})

    # HR: reject leave
    @extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Reject leave request",
        description="""Reject a pending leave request.""",
        request=None,
        responses={
            200: OpenApiResponse(description="Leave rejected successfully"),
            400: OpenApiResponse(description="Leave is not pending"),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Leave not found"),
        },
    )
    @action(detail=True, methods=['post'], permission_classes=[IsHR])
    def reject(self, request, pk=None):
        leave = self.get_object()
        try:
            LeaveService.reject_leave(leave, request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response({"status": "rejected"})

    @extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Leave analytics",
        description="""Provides aggregated leave statistics.""",
        parameters=[
            OpenApiParameter(
                name="year",
                type=int,
                required=False,
                description="Year for analytics (e.g. 2025)",
            ),
            OpenApiParameter(
                name="month",
                type=int,
                required=False,
                description="Optional month (1–12). If provided, returns monthly analytics.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Aggregated leave statistics by status"
            )
        },
    )
    @action(detail=False, methods=['get'], url_path='analytics', permission_classes=[IsHR])
    def analytics(self, request):
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        data = LeaveService.analytics(year, month)
        return Response(data)

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

@extend_schema(
    tags=["Dealers - Human Resource Management"],
    description=(
        "Manage salary components used in payroll calculations. "
        "Examples: Basic Salary, Allowances, Overtime, Deductions. "
        "These components are later assigned to employees."
    )
)
class SalaryComponentViewSet(viewsets.ModelViewSet):
    queryset = SalaryComponent.objects.all()
    serializer_class = SalaryComponentSerializer
    permission_classes = [IsAuthenticated, IsDealerOrHR]

@extend_schema(
    tags=["Dealers - Human Resource Management"],
    description=(
        "Assign salary components to individual employees. "
        "Each record links an employee with a salary component "
        "and a fixed or calculated amount. "
        "Used during payroll processing."
    )
)
class EmployeeSalaryViewSet(ModelViewSet):
    queryset = EmployeeSalary.objects.select_related("employee", "component")
    serializer_class = EmployeeSalarySerializer
    permission_classes = [IsAuthenticated, IsDealerOrHR]

@extend_schema(
    tags=["Dealers - Human Resource Management"],
    description=(
        "Manage overtime entries for employees. "
        "Overtime records are used to calculate additional pay "
        "during payroll processing. "
        "Finance users may audit and approve overtime data."
    )
)
class OvertimeEmployeeViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsDealerOrHR | IsFinance]
    serializer_class = OvertimeSerializer
    queryset = OvertimeEntry.objects.all()

