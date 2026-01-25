from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=20, unique=True)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.employee_id

class SalaryComponent(models.Model):
    EARNING = "earning"
    DEDUCTION = "deduction"

    COMPONENT_TYPE = [
        (EARNING, "Earning"),
        (DEDUCTION, "Deduction"),
    ]

    name = models.CharField(max_length=100)
    component_type = models.CharField(max_length=10, choices=COMPONENT_TYPE)
    is_taxable = models.BooleanField(default=True)
    is_pensionable = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class EmployeeSalary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    component = models.ForeignKey(SalaryComponent, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

class PayrollRun(models.Model):
    period = models.DateField()  # e.g. 2026-01-01
    status = models.CharField(
        max_length=10,
        choices=[
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("posted", "Posted"),
        ],
        default="draft"
    )
    created_at = models.DateTimeField(auto_now_add=True)

class PayrollItem(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    gross_earnings = models.DecimalField(max_digits=12, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)

class PayrollLine(models.Model):
    payroll_item = models.ForeignKey(PayrollItem, on_delete=models.CASCADE)
    component = models.ForeignKey(SalaryComponent, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)



