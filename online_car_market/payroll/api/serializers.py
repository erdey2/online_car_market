from rest_framework import serializers
from online_car_market.payroll.models import PayrollRun, PayrollItem, PayrollLine, SalaryComponent


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
        return PayrollLineSerializer(
            obj.payrollline_set.filter(component__component_type=SalaryComponent.EARNING),
            many=True
        ).data

    def get_deductions(self, obj):
        return PayrollLineSerializer(
            obj.payrollline_set.filter(component__component_type=SalaryComponent.DEDUCTION),
            many=True
        ).data

class PayrollRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRun
        fields = ["id", "period", "status", "created_at"]





