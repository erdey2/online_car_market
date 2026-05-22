from rest_framework import serializers
from online_car_market.payroll.models import (
    PayrollRun,
    PayrollItem,
    PayrollLine,
    SalaryComponent,
)


class PayrollLineSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="component.name")

    class Meta:
        model = PayrollLine
        fields = ["name", "amount"]


class PayslipSerializer(serializers.ModelSerializer):
    earnings = serializers.SerializerMethodField()
    deductions = serializers.SerializerMethodField()

    class Meta:
        model = PayrollItem
        fields = (
            "employee",
            "gross_earnings",
            "total_deductions",
            "net_salary",
            "earnings",
            "deductions",
        )

    def get_earnings(self, obj):
        lines = [
            line
            for line in obj.lines.all()
            if line.component.component_type == SalaryComponent.EARNING
        ]
        return PayrollLineSerializer(lines, many=True).data

    def get_deductions(self, obj):
        lines = [
            line
            for line in obj.lines.all()
            if line.component.component_type == SalaryComponent.DEDUCTION
        ]
        return PayrollLineSerializer(lines, many=True).data


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
