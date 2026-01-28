from django.contrib import admin
from online_car_market.payroll.models import Employee, EmployeeSalary, SalaryComponent

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "user", "hire_date", "is_active")

@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(admin.ModelAdmin):
    list_display = ("employee", "component", "amount")

@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "component_type", "is_taxable", "is_pensionable", "is_system")
