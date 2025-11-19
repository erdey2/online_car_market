from __future__ import annotations
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rolepermissions.checkers import has_role
import bleach
from ..models import Employee, Contract, Attendance, Leave
from online_car_market.hr.utils.pdf import generate_and_upload_pdf

User = get_user_model()

class EmployeeSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(write_only=True, required=True)
    user_email_display = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "user_email",
            "user_email_display",
            "full_name",
            "hire_date",
            "position",
            "salary",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_email_display", "full_name", "created_by", "created_at", "updated_at"]

    def get_full_name(self, obj: Employee) -> str:
        return f"{obj.user.profile.first_name} {obj.user.profile.last_name}".strip() or "Unknown"

    # Field-level validations
    def validate_hire_date(self, value: date) -> date:
        if value > date.today():
            raise serializers.ValidationError("Hire date cannot be in the future.")
        return value

    def validate_salary(self, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise serializers.ValidationError("Salary cannot be negative.")
        return value

    def validate_employee_email(self, email: str) -> User:
        """Resolve email → User + prevent duplicate Employee."""
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user with this email exists.")

        if self.instance:  # update
            if Employee.objects.filter(user=user).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("This user is already an employee.")
        else:  # create
            if hasattr(user, "employee_profile"):
                raise serializers.ValidationError("This user is already an employee.")
        return user

    def create(self, validated_data: dict) -> Employee:
        user = validated_data.pop("user_email")
        if "hire_date" not in validated_data:
            validated_data["hire_date"] = timezone.now().date()

        # Assign created_by from request.user
        request_user = self.context["request"].user
        return Employee.objects.create(user=user, created_by=request_user, **validated_data)

    def update(self, instance: Employee, validated_data: dict) -> Employee:
        # Never allow changing linked User
        validated_data.pop("user_email", None)
        return super().update(instance, validated_data)

class SignedUploadSerializer(serializers.Serializer):
    signed_document = serializers.FileField()

class FinalUploadSerializer(serializers.Serializer):
    final_document = serializers.FileField()

class ContractSerializer(serializers.ModelSerializer):
    employee_email = serializers.EmailField(write_only=True, required=True)
    employee_full_name = serializers.CharField(source='employee.user.profile.get_full_name', read_only=True)

    draft_document_url = serializers.URLField(read_only=True)
    employee_signed_document_url = serializers.URLField(read_only=True)
    final_document_url = serializers.URLField(read_only=True)

    class Meta:
        model = Contract
        fields = [
            'id', 'employee_email', 'employee_full_name',
            'employee_type', 'job_title', 'contract_salary', 'transport_allowance',
            'start_date', 'probation_end_date', 'end_date', 'terms',
            'status', 'draft_document_url', 'employee_signed_document_url',
            'final_document_url', 'created_at'
        ]
        read_only_fields = ['status', 'draft_document_url', 'final_document_url', 'created_at']

    def validate_terms(self, value):
        return bleach.clean(value, tags=[], attributes={})

    def validate(self, data):
        emp_type = data.get('employee_type')
        start = data.get('start_date')

        if emp_type == 'probation' and not data.get('probation_end_date'):
            raise serializers.ValidationError("Probation end date required.")
        if emp_type == 'temporary' and not data.get('end_date'):
            raise serializers.ValidationError("End date required for temporary contract.")
        return data

    def validate_employee_email(self, email):
        try:
            employee = Employee.objects.get(user__email=email)
            return employee
        except Employee.DoesNotExist:
            raise serializers.ValidationError(f"No employee found with email: {email}")

    def create(self, validated_data):
        request = self.context['request']
        if not has_role(request.user, ['hr', 'admin', 'super_admin']):
            raise serializers.ValidationError("Only HR can create contracts.")

        employee_instance = validated_data.pop('employee_email')

        contract = Contract.objects.create(
            employee=employee_instance,  # ← Now correct: Employee object
            created_by=request.user,
            status='draft',
            **validated_data
        )

        # Generate and upload PDF
        pdf_url = generate_and_upload_pdf(contract)
        contract.draft_document_url = pdf_url
        contract.status = 'draft'
        contract.save()

        return contract

class AttendanceSerializer(serializers.ModelSerializer):
    employee_email = serializers.EmailField(write_only=True, required=True)
    employee_email_display = serializers.EmailField(source="employee.user.email", read_only=True)
    employee_full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id",
            "employee_email",  # input
            "employee_email_display",  # output
            "employee_full_name",
            "entry_time",
            "exit_time",
            "date",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "employee_email_display", "employee_full_name", "created_at", "updated_at"]

    def get_employee_full_name(self, obj: Attendance) -> str:
        profile = obj.employee.user.profile
        return f"{profile.first_name} {profile.last_name}".strip() or "Unknown"

    def validate_employee_email(self, email: str) -> Employee:
        try:
            employee = Employee.objects.get(user__email=email)
            return employee
        except Employee.DoesNotExist:
            raise serializers.ValidationError("No employee with this email exists.")

    def validate(self, data: dict) -> dict:
        entry = data.get("entry_time")
        exit_ = data.get("exit_time")
        att_date = data.get("date", getattr(self.instance, "date", None))

        # Entry before exit
        if entry and exit_ and entry > exit_:
            raise serializers.ValidationError(
                "Entry time must be before or equal to exit time."
            )

        # No duplicate attendance for the same employee on the same day
        employee = data.get("employee") or (self.instance.employee if self.instance else None)
        if employee and att_date:
            qs = Attendance.objects.filter(employee=employee, date=att_date)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f"Attendance for {employee.user.email} on {att_date} already exists."
                )

        # Sanitize notes
        if "notes" in data:
            data["notes"] = bleach.clean(data["notes"], tags=[], attributes={})

        return data

    def create(self, validated_data: dict) -> Attendance:
        _require_hr_or_admin(self.context["request"])

        # Resolve employee
        employee = validated_data.pop("employee_email")  # This is Employee instance

        # Default date = today if not provided
        if "date" not in validated_data:
            validated_data["date"] = timezone.now().date()

        return Attendance.objects.create(employee=employee, **validated_data)

    def update(self, instance: Attendance, validated_data: dict) -> Attendance:
        _require_hr_or_admin(self.context["request"])

        # Never change employee
        validated_data.pop("employee_email", None)

        return super().update(instance, validated_data)

class LeaveSerializer(serializers.ModelSerializer):
    employee_email = serializers.EmailField(write_only=True, required=True)
    employee_email_display = serializers.EmailField(source="employee.user.email", read_only=True)
    employee_full_name = serializers.SerializerMethodField(read_only=True)
    approved_by_email = serializers.EmailField(source="approved_by.email", read_only=True)

    class Meta:
        model = Leave
        fields = [
            "id",
            "employee_email",  # input
            "employee_email_display",  # output
            "employee_full_name",  # output
            "start_date",
            "end_date",
            "reason",
            "status",
            "approved_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "employee_email_display", "employee_full_name", "approved_by_email", "created_at", "updated_at"]

    def get_employee_full_name(self, obj: Leave) -> str:
        profile = obj.employee.user.profile
        return f"{profile.first_name} {profile.last_name}".strip() or "Unknown"

    def validate_employee_email(self, email: str) -> Employee:
        try:
            employee = Employee.objects.get(user__email=email)
            return employee
        except Employee.DoesNotExist:
            raise serializers.ValidationError("No employee with this email exists.")

    def validate(self, data: dict) -> dict:
        start = data.get("start_date")
        end = data.get("end_date")
        employee = data.get("employee") or (self.instance.employee if self.instance else None)

        if start and end and start > end:
            raise serializers.ValidationError(
                "Leave start date must be before or equal to end date."
            )

        # No overlapping approved leaves
        if employee and start and end:
            overlap = Leave.objects.filter(
                employee=employee,
                status="approved",
                start_date__lte=end,
                end_date__gte=start,
            )
            if self.instance:
                overlap = overlap.exclude(pk=self.instance.pk)
            if overlap.exists():
                raise serializers.ValidationError(
                    "The employee already has an approved leave that overlaps with these dates."
                )

        # Clean reason
        if "reason" in data:
            data["reason"] = bleach.clean(data["reason"], tags=[], attributes={})

        return data

    def create(self, validated_data: dict) -> Leave:
        request = self.context["request"]
        if not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")

        # Resolve employee
        employee = validated_data.pop("employee_email")  # This is Employee instance

        # If the requester is the employee themselves → allow
        # If HR → allow (they can create for anyone)
        if not has_role(request.user, ["hr", "dealer"]):
            # Must be requesting for themselves
            if employee.user != request.user:
                raise serializers.ValidationError("You can only request leave for yourself.")

        return Leave.objects.create(employee=employee, **validated_data)

    def update(self, instance: Leave, validated_data: dict) -> Leave:
        _require_hr_or_admin(self.context["request"])

        # Never allow changing employee
        validated_data.pop("employee_email", None)

        # Auto-set approved_by when status changes
        new_status = validated_data.get("status")
        if new_status in ("approved", "denied") and instance.status == "pending":
            validated_data["approved_by"] = self.context["request"].user

        return super().update(instance, validated_data)
