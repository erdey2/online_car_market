from __future__ import annotations
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from rest_framework import serializers
from rolepermissions.checkers import has_role
import bleach
from ..models import Employee, Contract, Attendance, Leave, SalaryComponent, EmployeeSalary, OvertimeEntry
from online_car_market.hr.utils.pdf import generate_and_upload_pdf
from online_car_market.dealers.models import DealerStaff

User = get_user_model()

class EmployeeSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(write_only=True, required=True)
    user_email_display = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    salary = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    components = serializers.SerializerMethodField(read_only=True)
    overtime_entries = serializers.SerializerMethodField(read_only=True)
    total_overtime_hours = serializers.SerializerMethodField(read_only=True)

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

            "components",
            "overtime_entries",
            "total_overtime_hours",

            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "user_email_display",
            "full_name",
            "salary",
            "components",
            "overtime_entries",
            "total_overtime_hours",
            "created_by",
            "created_at",
            "updated_at"
        ]

    def get_full_name(self, obj):
        profile = getattr(obj.user, "profile", None)

        if not profile:
            return "Unknown"

        return f"{profile.first_name} {profile.last_name}".strip()

    def _employee_salaries(self, obj):
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "employeesalary_set" in obj._prefetched_objects_cache
        ):
            return obj.employeesalary_set.all()

        return EmployeeSalary.objects.select_related(
            "component"
        ).filter(employee=obj)

    def get_salary(self, obj):
        for salary in self._employee_salaries(obj):
            if salary.component.name.lower() == "basic salary":
                return salary.amount

        return None

    def get_components(self, obj):
        return SimpleEmployeeSerializer(
            self._employee_salaries(obj),
            many=True
        ).data

    def get_overtime_entries(self, obj):
        overtime_qs = obj.overtime_entries.all().order_by("-date")

        return OvertimeSerializer(
            overtime_qs,
            many=True
        ).data

    def get_total_overtime_hours(self, obj):
        total = obj.overtime_entries.aggregate(
            total=Sum("hours")
        )["total"]

        return total or 0

    def validate_hire_date(self, value):
        if value > date.today():
            raise serializers.ValidationError(
                "Hire date cannot be in the future."
            )

        return value

    def validate_user_email(self, email):
        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:
            raise serializers.ValidationError(
                "No user with this email exists."
            )

        if self.instance:
            if Employee.objects.filter(user=user).exclude(
                pk=self.instance.pk
            ).exists():
                raise serializers.ValidationError(
                    "This user is already an employee."
                )

        else:
            if hasattr(user, "employee_profile"):
                raise serializers.ValidationError(
                    "This user is already an employee."
                )

        return user

    @transaction.atomic
    def create(self, validated_data):
        user = validated_data.pop("user_email")
        salary = validated_data.pop("salary", None)

        if "hire_date" not in validated_data:
            validated_data["hire_date"] = timezone.now().date()

        request_user = self.context["request"].user

        dealer = getattr(
            request_user.profile,
            "dealer_profile",
            None
        )

        if not dealer:
            staff = DealerStaff.objects.filter(
                user=request_user,
                role="hr"
            ).first()

            if not staff:
                raise serializers.ValidationError(
                    "Not allowed."
                )

        employee = Employee.objects.create(
            user=user,
            created_by=request_user,
            salary=salary,
            **validated_data
        )

        if salary:
            basic_salary_component, created = (
                SalaryComponent.objects.get_or_create(
                    name="Basic Salary",
                    defaults={
                        "component_type": SalaryComponent.EARNING,
                        "is_taxable": True,
                        "is_pensionable": True,
                        "is_system": True,
                    }
                )
            )

            EmployeeSalary.objects.create(
                employee=employee,
                component=basic_salary_component,
                amount=salary
            )

        return employee

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
            "employee_email",          # input only
            "employee_email_display",  # output only
            "employee_full_name",
            "entry_time",
            "exit_time",
            "date",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "employee_email_display",
            "employee_full_name",
            "created_at",
            "updated_at",
        ]

    def get_employee_full_name(self, obj: Attendance) -> str:
        profile = obj.employee.user.profile
        full = f"{profile.first_name} {profile.last_name}".strip()
        return full or "Unknown"

    def validate_employee_email(self, email: str) -> Employee:
        try:
            return Employee.objects.get(user__email=email)
        except Employee.DoesNotExist:
            raise serializers.ValidationError("No employee with this email exists.")

    def validate(self, data: dict) -> dict:
        entry = data.get("entry_time")
        exit_ = data.get("exit_time")

        # Ensure entry is before exit
        if entry and exit_ and entry > exit_:
            raise serializers.ValidationError("Entry time must be before or equal to exit time.")

        # Check duplicate attendance for the same employee/day
        employee = data.get("employee") or (self.instance.employee if self.instance else None)
        att_date = data.get("date") or (self.instance.date if self.instance else None)

        if employee and att_date:
            qs = Attendance.objects.filter(employee=employee, date=att_date)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    f"Attendance for {employee.user.email} on {att_date} already exists."
                )

        # Sanitize notes input
        if "notes" in data:
            data["notes"] = bleach.clean(data["notes"], tags=[], attributes={})

        return data

    def create(self, validated_data: dict) -> Attendance:
        # Resolve employee object
        employee = validated_data.pop("employee_email")

        # If date not provided → use today's date
        if "date" not in validated_data:
            validated_data["date"] = timezone.now().date()

        return Attendance.objects.create(employee=employee, **validated_data)

    def update(self, instance: Attendance, validated_data: dict) -> Attendance:
        # Employee cannot be changed
        validated_data.pop("employee_email", None)
        return super().update(instance, validated_data)

class LeaveSerializer(serializers.ModelSerializer):
    employee_email = serializers.EmailField(write_only=True, required=True)
    employee_email_display = serializers.EmailField(
        source="employee.user.email", read_only=True
    )
    employee_full_name = serializers.SerializerMethodField(read_only=True)
    approved_by_email = serializers.EmailField(
        source="approved_by.email", read_only=True
    )

    class Meta:
        model = Leave
        fields = [
            "id",
            "employee_email",
            "employee_email_display",
            "employee_full_name",
            "start_date",
            "end_date",
            "reason",
            "status",
            "approved_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "employee_email_display",
            "employee_full_name",
            "approved_by_email",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_employee_full_name(self, obj):
        profile = getattr(obj.employee.user, "profile", None)
        if not profile:
            return ""
        return f"{profile.first_name} {profile.last_name}".strip()

    def validate_employee_email(self, email):
        try:
            return Employee.objects.get(user__email=email)
        except Employee.DoesNotExist:
            raise serializers.ValidationError("No employee with this email exists.")

    def validate(self, data):
        start = data.get("start_date")
        end = data.get("end_date")
        employee = data.get("employee")

        if start and end and start > end:
            raise serializers.ValidationError(
                "Start date must be before end date."
            )

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
                    "This employee already has approved leave during this time range."
                )

        if "reason" in data:
            data["reason"] = bleach.clean(
                data["reason"], tags=[], attributes={}
            )

        return data

    def create(self, validated_data):
        # REMOVE employee_email before model creation
        employee = validated_data.pop("employee_email")

        return Leave.objects.create(
            employee=employee,
            **validated_data
        )

class SalaryComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryComponent
        fields = ["id", "name", "component_type"]
        read_only_fields = ["id"]

class SimpleEmployeeSerializer(serializers.ModelSerializer):
    component_name = serializers.CharField(source="component.name", read_only=True)

    class Meta:
        model = EmployeeSalary
        fields = ["id", "component_name", "amount"]

class EmployeeSalarySerializer(serializers.ModelSerializer):
    employee_email = serializers.EmailField(
        source="employee.user.email", read_only=True
    )
    component_name = serializers.CharField(
        source="component.name", read_only=True
    )

    def validate_amount(self, value: Decimal) -> Decimal:
        if value < 0:
            raise serializers.ValidationError("Amount cannot be negative.")
        return value

    class Meta:
        model = EmployeeSalary
        fields = [
            "id",
            "employee",
            "employee_email",
            "component",
            "component_name",
            "amount",
        ]

class OvertimeSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField(read_only=True)
    overtime_type_display = serializers.CharField(
        source="get_overtime_type_display",
        read_only=True
    )

    class Meta:
        model = OvertimeEntry
        fields = [
            "id",
            "employee",
            "employee_name",
            "overtime_type",
            "overtime_type_display",
            "hours",
            "approved",
            "date",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]

    def get_employee_name(self, obj):
        profile = getattr(obj.employee.user, "profile", None)

        if not profile:
            return obj.employee.user.email

        return f"{profile.first_name} {profile.last_name}".strip()

    def validate_hours(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Overtime hours must be greater than zero."
            )

        if value > Decimal("24"):
            raise serializers.ValidationError(
                "Overtime hours cannot exceed 24 hours."
            )

        return value

    def validate_date(self, value):
        if value and value > timezone.now().date():
            raise serializers.ValidationError(
                "Overtime date cannot be in the future."
            )

        return value

    def validate(self, attrs):
        employee = attrs.get("employee")

        if not employee:
            raise serializers.ValidationError(
                {"employee": "Employee is required."}
            )

        return attrs


