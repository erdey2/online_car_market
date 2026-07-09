from rest_framework import serializers
from online_car_market.hr.models import Employee
from online_car_market.payroll.models import PayrollRun, PayrollItem, PayrollLine, SalaryComponent

class PayrollLineSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="component.name")

    class Meta:
        model = PayrollLine
        fields = ["name", "amount"]

class PayrollRunSuccessSerializer(serializers.Serializer):
    detail = serializers.CharField()
    data = serializers.DictField()

class PayrollRunErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()

class PayslipEmployeeSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "contact",
            "position",
            "hire_date",
        ]

    def _profile(self, obj):
        if obj.user:
            return getattr(obj.user, "profile", None)
        return None

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

    def get_contact(self, obj):
        profile = self._profile(obj)

        if profile and profile.contact:
            return profile.contact

        return obj.contact

    def get_email(self, obj):
        if obj.user:
            return obj.user.email

        return obj.email

    def get_full_name(self, obj):
        first = self.get_first_name(obj)
        last = self.get_last_name(obj)

        name = f"{first or ''} {last or ''}".strip()

        if name:
            return name

        email = self.get_email(obj)

        if email:
            return email

        return "Unknown Employee"


class PayslipSerializer(serializers.ModelSerializer):
    employee = PayslipEmployeeSerializer(read_only=True)

    payroll_run = serializers.PrimaryKeyRelatedField(read_only=True)
    pay_period_start = serializers.DateField(
        source="payroll_run.pay_period_start",
        read_only=True
    )
    pay_period_end = serializers.DateField(
        source="payroll_run.pay_period_end",
        read_only=True
    )
    processed_at = serializers.DateTimeField(
        source="payroll_run.created_at",
        read_only=True
    )

    earnings = serializers.SerializerMethodField()
    deductions = serializers.SerializerMethodField()

    class Meta:
        model = PayrollItem
        fields = [
            "employee",
            "payroll_run",
            "pay_period_start",
            "pay_period_end",
            "processed_at",
            "gross_earnings",
            "total_deductions",
            "net_salary",
            "earnings",
            "deductions",
        ]

    def get_earnings(self, obj):
        queryset = obj.lines.filter(
            component__component_type=SalaryComponent.EARNING
        ).select_related("component")

        return PayrollLineSerializer(queryset, many=True).data

    def get_deductions(self, obj):
        queryset = obj.lines.filter(
            component__component_type=SalaryComponent.DEDUCTION
        ).select_related("component")

        return PayrollLineSerializer(queryset, many=True).data

class PayrollRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRun
        fields = ["id", "period", "status", "created_at"]
        extra_kwargs = {
            "period": {
                "help_text": "Payroll period in YYYY-MM format (example: 2026-05)."
            },
            "status": {
                "help_text": (
                    "Payroll workflow status:\n"
                    "- draft → created but not processed\n"
                    "- processed → payroll calculated\n"
                    "- approved → payroll verified and locked\n"
                    "- posted → final and immutable"
                )
            },
            "created_at": {
                "help_text": "Timestamp when the payroll run was created."
            },
        }
