from django.contrib import admin
from online_car_market.payroll.models import Employee

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "user", "hire_date", "is_active")

