from rest_framework import serializers
from online_car_market.payroll.models import (
    Employee,
    PayrollRun,
    PayrollItem,
    PayrollLine,
    SalaryComponent
)

# Salary Component
class SalaryComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryComponent
        fields = ["id", "name", "component_type"]


# Payroll Line (earnings/deductions
class PayrollLineSerializer(serializers.ModelSerializer):
    component = SalaryComponentSerializer()

    class Meta:
        model = PayrollLine
        fields = ["component", "amount"]


# Payroll Item (Payslip)
class PayrollItemSerializer(serializers.ModelSerializer):
    lines = PayrollLineSerializer(
        many=True,
        source="payrollline_set"
    )

    class Meta:
        model = PayrollItem
        fields = [
            "employee",
            "gross_earnings",
            "total_deductions",
            "net_salary",
            "lines",
        ]

# Payroll Run
class PayrollRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollRun
        fields = ["id", "period", "status", "created_at"]
