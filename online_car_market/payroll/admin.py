from django.contrib import admin
from online_car_market.payroll.models import Employee, SalaryComponent
from online_car_market.hr.models import EmployeeSalary, OvertimeEntry

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "hire_date", "is_active")

@admin.register(EmployeeSalary)
class EmployeeSalaryAdmin(admin.ModelAdmin):
    list_display = ("employee", "component", "amount")

@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "component_type", "is_taxable", "is_pensionable", "is_system")

@admin.register(OvertimeEntry)
class OvertimeEntryAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "date",
        "overtime_type",
        "hours",
        "approved",
        "created_at",
    )
    list_filter = ("approved", "overtime_type", "date")
    search_fields = ("employee__user__email",)

