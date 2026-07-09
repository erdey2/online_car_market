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
    full_name = serializers.SerializerMethodField()

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

    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()

        if name:
            return name

        if obj.email:
            return obj.email

        if obj.user:
            return obj.user.email

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
