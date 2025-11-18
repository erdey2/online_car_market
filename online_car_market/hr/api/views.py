from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from online_car_market.users.permissions.drf_permissions import IsHR
from online_car_market.users.permissions.business_permissions import IsERPUser
from ..models import Employee, Contract, Attendance, Leave
from .serializers import EmployeeSerializer, ContractSerializer, AttendanceSerializer, LeaveSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="List all employees",
        description="Retrieve a list of all registered employees, including position, department, and hiring date.",
    ),
    retrieve=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Retrieve employee details",
        description="Fetch detailed information about a specific employee by their ID.",
    ),
    create=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Add a new employee",
        description="Create a new employee record with details such as position, department, and date hired.",
    ),
    update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Update employee information",
        description="Modify existing employee details including department, position, and active status.",
    ),
    partial_update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Partially update employee information",
        description="Update specific fields of an employee record without overwriting the entire object.",
    ),
    destroy=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Delete employee record",
        description="Remove an employee record permanently from the system.",
    ),
)
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsHR]


@extend_schema_view(
    list=extend_schema(tags=["Contracts"], summary="List all contracts"),
    create=extend_schema(tags=["Contracts"], summary="Create a new contract"),
    retrieve=extend_schema(tags=["Contracts"], summary="Get contract details"),
    update=extend_schema(tags=["Contracts"], summary="Update a contract"),
    partial_update=extend_schema(tags=["Contracts"], summary="Partially update a contract"),
    destroy=extend_schema(tags=["Contracts"], summary="Delete a contract"),
)
class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.all().select_related("employee__user")
    serializer_class = ContractSerializer
    permission_classes = [IsERPUser]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


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


@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="List all leave requests",
        description="Retrieve all employee leave requests including pending, approved, and denied statuses.",
    ),
    create=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Request leave",
        description="Employees or HR staff can create a leave request specifying the duration and reason.",
    ),
    retrieve=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="View leave details",
        description="Retrieve detailed information about a specific leave request.",
    ),
    update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Approve or deny leave",
        description="HR can update a leave request to approve or deny it. This automatically logs who reviewed it.",
    ),
    partial_update=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Partially approve or deny leave",
        description="HR can partially update specific fields of a leave request, such as status or reviewer.",
    ),
    destroy=extend_schema(
        tags=["Dealers - Human Resource Management"],
        summary="Delete leave request",
        description="Remove a leave request from the system if it was created by mistake or no longer needed.",
    ),
)
class LeaveViewSet(viewsets.ModelViewSet):
    queryset = Leave.objects.select_related("employee__user", "approved_by").all()
    serializer_class = LeaveSerializer

    def get_permissions(self):
        """
        - Employees can CREATE leave requests (for themselves)
        - Only HR can update/delete/approve
        """
        if self.action == 'create':
            return [permissions.IsAuthenticated()]  # Any logged-in user
        return [IsHR()]

    def perform_update(self, serializer):
        # Automatically log the HR reviewer if leave status changes
        if serializer.validated_data.get("status") in ["approved", "denied"]:
            serializer.save(reviewed_by=self.request.user)
        else:
            serializer.save()
