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

''' class EmployeeSerializer(serializers.ModelSerializer):
    login_email = serializers.SerializerMethodField(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    salary = serializers.SerializerMethodField(read_only=True)
    components = serializers.SerializerMethodField(read_only=True)
    overtime_entries = serializers.SerializerMethodField(read_only=True)
    total_overtime_hours = serializers.SerializerMethodField(read_only=True)
    has_account = serializers.SerializerMethodField()

    # Return profile values if account exists
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "last_name",
            "contact",
            "email",
            "login_email",
            "has_account",
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
            "login_email",
            "full_name",
            "salary",
            "components",
            "overtime_entries",
            "total_overtime_hours",
            "created_by",
            "created_at",
            "updated_at",
        ]

    # Helpers

    def _profile(self, obj):
        if obj.user:
            return getattr(obj.user, "profile", None)
        return None

    # Employee information

    def get_first_name(self, obj):
        profile = self._profile(obj)
        if profile and profile.first_name:
            return profile.first_name
        return obj.first_name

    def get_last_name(self, obj):
        profile = self._profile(obj)
        if profile and profile.last_name:
            return profile.last_name
        return obj.last_name

    def get_email(self, obj):
        if obj.user:
            return obj.user.email
        return obj.email

    def get_contact(self, obj):
        profile = self._profile(obj)
        if profile and profile.contact:
            return profile.contact
        return obj.contact

    def get_login_email(self, obj):
        return obj.user.email if obj.user else None

    def get_full_name(self, obj):
        profile = self._profile(obj)

        if profile:
            name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
            if name:
                return name
            return obj.user.email

        name = f"{obj.first_name or ''} {obj.last_name or ''}".strip()
        if name:
            return name

        return obj.email

    def get_has_account(self, obj):
        return obj.user is not None

    # Salary
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
        return OvertimeSerializer(
            obj.overtime_entries.all().order_by("-date"),
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

    @transaction.atomic
    def create(self, validated_data):
        salary = validated_data.pop("salary", None)

        request_user = self.context["request"].user

        dealer = getattr(
            request_user.profile,
            "dealer_profile",
            None,
        )

        if not dealer:
            staff = DealerStaff.objects.filter(
                user=request_user,
                role="hr",
            ).first()

            if not staff:
                raise serializers.ValidationError(
                    "You are not allowed to create employees."
                )

        employee = Employee.objects.create(
            created_by=request_user,
            salary=salary,
            **validated_data,
        )

        if salary:
            basic_salary_component, _ = SalaryComponent.objects.get_or_create(
                name="Basic Salary",
                defaults={
                    "component_type": SalaryComponent.EARNING,
                    "is_taxable": True,
                    "is_pensionable": True,
                    "is_system": True,
                },
            )

            EmployeeSalary.objects.create(
                employee=employee,
                component=basic_salary_component,
                amount=salary,
            )

        return employee '''

class EmployeeSerializer(serializers.ModelSerializer):
    # Writable fields
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    contact = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_null=True)
    salary = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
    )

    # Read-only fields
    login_email = serializers.SerializerMethodField(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    components = serializers.SerializerMethodField(read_only=True)
    overtime_entries = serializers.SerializerMethodField(read_only=True)
    total_overtime_hours = serializers.SerializerMethodField(read_only=True)
    has_account = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "last_name",
            "contact",
            "email",
            "login_email",
            "has_account",
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
            "login_email",
            "has_account",
            "full_name",
            "components",
            "overtime_entries",
            "total_overtime_hours",
            "created_by",
            "created_at",
            "updated_at",
        ]

    # Helpers

    def _profile(self, obj):
        if obj.user:
            return getattr(obj.user, "profile", None)
        return None

    def _employee_salaries(self, obj):
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "employeesalary_set" in obj._prefetched_objects_cache
        ):
            return obj.employeesalary_set.all()

        return EmployeeSalary.objects.select_related(
            "component"
        ).filter(employee=obj)

    # Representation

    def to_representation(self, instance):
        data = super().to_representation(instance)

        profile = self._profile(instance)

        if profile:
            data["first_name"] = profile.first_name or instance.first_name
            data["last_name"] = profile.last_name or instance.last_name
            data["contact"] = profile.contact or instance.contact
            data["email"] = instance.user.email

        data["salary"] = self.get_salary(instance)

        return data

    # Computed fields

    def get_login_email(self, obj):
        return obj.user.email if obj.user else None

    def get_has_account(self, obj):
        return obj.user is not None

    def get_full_name(self, obj):
        profile = self._profile(obj)

        if profile:
            name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()

            if name:
                return name

            return obj.user.email

        return (
            f"{obj.first_name or ''} {obj.last_name or ''}".strip()
            or obj.email
        )

    def get_salary(self, obj):
        for employee_salary in self._employee_salaries(obj):
            if employee_salary.component.name.lower() == "basic salary":
                return employee_salary.amount

        return obj.salary

    def get_components(self, obj):
        return SimpleEmployeeSerializer(
            self._employee_salaries(obj),
            many=True
        ).data

    def get_overtime_entries(self, obj):
        return OvertimeSerializer(
            obj.overtime_entries.all().order_by("-date"),
            many=True
        ).data

    def get_total_overtime_hours(self, obj):
        total = obj.overtime_entries.aggregate(
            total=Sum("hours")
        )["total"]

        return total or 0

    # Validation

    def validate_hire_date(self, value):
        if value > date.today():
            raise serializers.ValidationError(
                "Hire date cannot be in the future."
            )

        return value

    # Create

    @transaction.atomic
    def create(self, validated_data):
        salary = validated_data.pop("salary", None)

        employee = Employee.objects.create(
            created_by=self.context["request"].user,
            salary=salary,
            **validated_data,
        )

        if salary is not None:
            basic_salary_component, _ = SalaryComponent.objects.get_or_create(
                name="Basic Salary",
                defaults={
                    "component_type": SalaryComponent.EARNING,
                    "is_taxable": True,
                    "is_pensionable": True,
                    "is_system": True,
                },
            )

            EmployeeSalary.objects.create(
                employee=employee,
                component=basic_salary_component,
                amount=salary,
            )

        return employee

    # Update

    @transaction.atomic
    def update(self, instance, validated_data):
        salary = validated_data.pop("salary", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if salary is not None:
            basic_salary_component, _ = SalaryComponent.objects.get_or_create(
                name="Basic Salary",
                defaults={
                    "component_type": SalaryComponent.EARNING,
                    "is_taxable": True,
                    "is_pensionable": True,
                    "is_system": True,
                },
            )

            EmployeeSalary.objects.update_or_create(
                employee=instance,
                component=basic_salary_component,
                defaults={
                    "amount": salary,
                },
            )

            instance.salary = salary
            instance.save(update_fields=["salary"])

        return instance

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
    employee = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        write_only=True
    )

    employee_email = serializers.SerializerMethodField(read_only=True)
    employee_full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id",
            "employee",
            "employee_email",
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
            "employee_email",
            "employee_full_name",
            "created_at",
            "updated_at",
        ]

    def get_employee_email(self, obj):
        employee = obj.employee

        if employee.user:
            return employee.user.email

        return employee.email

    def get_employee_full_name(self, obj):
        employee = obj.employee

        if employee.user:
            profile = getattr(employee.user, "profile", None)

            if profile:
                full = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
                if full:
                    return full

            return employee.user.email

        full = f"{employee.first_name or ''} {employee.last_name or ''}".strip()

        return full or employee.email or "Unknown"

    def validate(self, attrs):
        entry = attrs.get("entry_time")
        exit_ = attrs.get("exit_time")

        if entry and exit_ and entry > exit_:
            raise serializers.ValidationError(
                "Entry time must be before or equal to exit time."
            )

        employee = attrs.get(
            "employee",
            getattr(self.instance, "employee", None)
        )

        att_date = attrs.get(
            "date",
            getattr(self.instance, "date", timezone.now().date())
        )

        if employee:
            qs = Attendance.objects.filter(
                employee=employee,
                date=att_date
            )

            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                identifier = (
                    employee.user.email
                    if employee.user
                    else employee.email
                    or employee.first_name
                    or f"Employee #{employee.pk}"
                )

                raise serializers.ValidationError({
                    "date": f"Attendance for {identifier} on {att_date} already exists."
                })

        if "notes" in attrs:
            attrs["notes"] = bleach.clean(
                attrs["notes"],
                tags=[],
                attributes={}
            )

        return attrs

    def create(self, validated_data):
        if "date" not in validated_data:
            validated_data["date"] = timezone.now().date()

        return Attendance.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("employee", None)
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
        employee = obj.employee

        if not employee:
            return None

        name = f"{employee.first_name} {employee.last_name}".strip()

        if name:
            return name

        return employee.email or (
            employee.user.email if employee.user else None
        )

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


