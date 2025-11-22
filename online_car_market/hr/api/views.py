from django.utils import timezone
from ..models import Employee, Contract, Attendance, Leave
from .serializers import (EmployeeSerializer, ContractSerializer, AttendanceSerializer,
                          LeaveSerializer, SignedUploadSerializer, FinalUploadSerializer)
from cloudinary.uploader import upload
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rolepermissions.checkers import has_role
from online_car_market.users.permissions.drf_permissions import IsHR
from online_car_market.users.permissions.business_permissions import IsHRorDealer
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiResponse
from templated_mail.mail import BaseEmailMessage


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
        if contract.status != 'draft':
            return Response({"detail": "Already sent"}, status=400)

        contract.status = 'sent_to_employee'
        contract.save()

        BaseEmailMessage(
            template_name='email/contract_sent.html',
            context={
                'name': contract.employee.user.profile.get_full_name(),
                'pdf_url': contract.draft_document_url
            }
        ).send(to=[contract.employee.user.email])

        return Response({"detail": "Sent!", "pdf_url": contract.draft_document_url})

    @action(detail=True, methods=['post'])
    def upload_signed(self, request, pk=None):
        contract = self.get_object()
        if contract.status != 'sent_to_employee':
            return Response({"detail": "Not sent yet"}, status=400)

        file = request.FILES.get('signed_document')
        if not file:
            return Response({"detail": "File required"}, status=400)

        result = upload(
            file.read(),
            folder="contracts/drafts/",
            resource_type="raw",
            format="pdf",
            type="upload",
            access_mode="public",
            use_filename=True,
            unique_filename=False,
            overwrite=True
        )
        contract.employee_signed_document_url = result['secure_url']
        contract.employee_signed_at = timezone.now()
        contract.status = 'signed_by_employee'
        contract.save()

        return Response({"detail": "Signed document uploaded"})

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        contract = self.get_object()
        if contract.status != 'signed_by_employee':
            return Response({"detail": "Employee must sign first"}, status=400)

        file = request.FILES.get('final_document')
        if not file:
            return Response({"detail": "Final document required"}, status=400)

        result = upload(
            file.read(),
            folder="contracts/drafts/",
            resource_type="raw",
            format="pdf",
            type="upload",
            access_mode="public",
            use_filename=True,
            unique_filename=False,
            overwrite=True
        )
        contract.final_document_url = result['secure_url']
        contract.finalized_by = request.user
        contract.finalized_at = timezone.now()
        contract.status = 'active'
        contract.save()

        BaseEmailMessage(
            template_name='email/contract_active.html',
            context={
                'name': contract.employee.user.profile.get_full_name(),
                'pdf_url': contract.final_document_url
            }
        ).send(to=[contract.employee.user.email])

        return Response({"detail": "Contract is now ACTIVE!", "final_pdf": contract.final_document_url})

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
