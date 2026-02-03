from rest_framework import serializers
from online_car_market.payroll.models import (Employee, PayrollRun, PayrollItem,
                                              PayrollLine, SalaryComponent, EmployeeSalary,
                                              OvertimeEntry
                                              )

class SalaryComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryComponent
        fields = ["id", "name", "component_type"]
        read_only_fields = ["id"]

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

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ["id", "user", "employee_id", "hire_date", "is_active"]

class EmployeeSalarySerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(
        source="employee.employee_id", read_only=True
    )
    component_name = serializers.CharField(
        source="component.name", read_only=True
    )

    class Meta:
        model = EmployeeSalary
        fields = [
            "id",
            "employee",
            "employee_id",
            "component",
            "component_name",
            "amount",
        ]

class OvertimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OvertimeEntry
        fields = ['employee', 'payroll_run', 'overtime_type', 'hours', 'created_at']
        read_only_fields = ['employee', 'payroll_run', 'created_at']



