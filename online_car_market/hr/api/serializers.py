from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Any
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rolepermissions.checkers import has_role
import bleach
from ..models import Employee, Contract, Attendance, Leave

User = get_user_model()

# Helper – role check (used in create / update)
def _require_hr_or_admin(request) -> None:
    """Utility used in create / update."""
    if not request.user.is_authenticated:
        raise serializers.ValidationError("Authentication required.")
    if not has_role(request.user, ["hr", "dealer"]):
        raise serializers.ValidationError(
            "Only HR staff or dealer may perform this action."
        )

# EmployeeSerializer
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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user_email_display", "full_name", "created_at", "updated_at"]

    def get_full_name(self, obj: Employee) -> str:
        return (
            f"{obj.user.profile.first_name} {obj.user.profile.last_name}".strip()
            or "Unknown"
        )

    # Field-level validation
    def validate_hire_date(self, value: date) -> date:
        if value > date.today():
            raise serializers.ValidationError("Hire date cannot be in the future.")
        return value

    def validate_salary(self, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise serializers.ValidationError("Salary cannot be negative.")
        return value

    def validate_user_email(self, email: str) -> User:
        """Resolve email → User + prevent duplicate Employee."""
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user with this email exists.")

        # One Employee per User (OneToOneField)
        if self.instance:  # update
            if Employee.objects.filter(user=user).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("This user is already an employee.")
        else:  # create
            if hasattr(user, "employee_profile"):
                raise serializers.ValidationError("This user is already an employee.")
        return user

    def create(self, validated_data: dict) -> Employee:
        _require_hr_or_admin(self.context["request"])

        # `user_email` is a User instance returned from validate_user_email()
        user = validated_data.pop("user_email")

        # Default hire_date = today if not supplied
        if "hire_date" not in validated_data:
            validated_data["hire_date"] = timezone.now().date()

        return Employee.objects.create(user=user, **validated_data)


    # UPDATE – never allow changing the linked user
    def update(self, instance: Employee, validated_data: dict) -> Employee:
        _require_hr_or_admin(self.context["request"])

        # Prevent changing the OneToOne relation
        validated_data.pop("user_email", None)

        return super().update(instance, validated_data)

# ----------------------------------------------------------------------
# ContractSerializer
# ----------------------------------------------------------------------
class ContractSerializer(serializers.ModelSerializer):
    employee_email = serializers.EmailField(source="employee.user.email", read_only=True)

    class Meta:
        model = Contract
        fields = [
            "id",
            "employee_email",
            "start_date",
            "end_date",
            "terms",
            "salary",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    # ------------------------------------------------------------------
    def validate_salary(self, value: float) -> float:
        if value <= 0:
            raise serializers.ValidationError("Contract salary must be greater than zero.")
        return value

    def validate(self, data: dict) -> dict:
        start = data.get("start_date")
        end = data.get("end_date")

        if start and end and start > end:
            raise serializers.ValidationError(
                "Contract start date must be before or equal to end date."
            )

        # Clean HTML / unsafe input
        if "terms" in data:
            data["terms"] = bleach.clean(data["terms"], tags=[], attributes={})

        # Only ONE ACTIVE contract per employee
        employee = data.get("employee") or (self.instance.employee if self.instance else None)
        if employee:
            qs = Contract.objects.filter(employee=employee, status="active")
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError(
                    "The employee already has an active contract."
                )

        return data

    def create(self, validated_data: dict) -> Contract:
        _require_hr_or_admin(self.context["request"])
        return super().create(validated_data)

    def update(self, instance: Contract, validated_data: dict) -> Contract:
        _require_hr_or_admin(self.context["request"])

        # Auto-expire if end_date passed
        if validated_data.get("end_date") and validated_data["end_date"] < date.today():
            validated_data.setdefault("status", "expired")

        return super().update(instance, validated_data)


# ----------------------------------------------------------------------
# AttendanceSerializer
# ----------------------------------------------------------------------
class AttendanceSerializer(serializers.ModelSerializer):
    employee_email = serializers.EmailField(source="employee.user.email", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id",
            "employee_email",
            "entry_time",
            "exit_time",
            "date",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    # ------------------------------------------------------------------
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
        return super().create(validated_data)

    def update(self, instance: Attendance, validated_data: dict) -> Attendance:
        _require_hr_or_admin(self.context["request"])
        return super().update(instance, validated_data)

# ----------------------------------------------------------------------
# LeaveSerializer
# ----------------------------------------------------------------------
class LeaveSerializer(serializers.ModelSerializer):
    employee_email = serializers.EmailField(source="employee.user.email", read_only=True)
    approved_by_email = serializers.EmailField(source="approved_by.email", read_only=True)

    class Meta:
        model = Leave
        fields = [
            "id",
            "employee_email",
            "start_date",
            "end_date",
            "reason",
            "status",
            "approved_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "approved_by_email", "created_at", "updated_at"]

    # ------------------------------------------------------------------
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
        # Employees can request leave; HR approves/denies
        request = self.context["request"]
        if not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")
        # Any authenticated employee can request; HR can also create directly
        return super().create(validated_data)

    def update(self, instance: Leave, validated_data: dict) -> Leave:
        _require_hr_or_admin(self.context["request"])

        # When status changes to approved/denied, record who did it
        new_status = validated_data.get("status")
        if new_status in ("approved", "denied") and instance.status == "pending":
            validated_data["approved_by"] = self.context["request"].user

        return super().update(instance, validated_data)
