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

    class Meta:
        unique_together = ("employee", "component")

class PayrollRun(models.Model):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"

    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (APPROVED, "Approved"),
        (POSTED, "Posted"),
    ]

    period = models.DateField()  # e.g. 2026-01-01
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["period"],
                name="unique_payroll_per_period"
            )
        ]

class PayrollItem(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    gross_earnings = models.DecimalField(max_digits=12, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2)
    net_salary = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["payroll_run", "employee"],
                name="unique_payroll_item_per_employee"
            )
        ]

class PayrollLine(models.Model):
    payroll_item = models.ForeignKey(PayrollItem, on_delete=models.CASCADE)
    component = models.ForeignKey(SalaryComponent, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

class OvertimeEntry(models.Model):
    OVERTIME_TYPE_CHOICES = [
        ("1.5", "Normal Overtime (1.5x)"),
        ("1.75", "Weekend Overtime (1.75x)"),
        ("2.0", "Special Overtime (2.0x)"),
        ("2.5", "Holiday Overtime (2.5x)"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    payroll_run = models.ForeignKey("PayrollRun", on_delete=models.CASCADE)
    overtime_type = models.CharField(max_length=4, choices=OVERTIME_TYPE_CHOICES)
    hours = models.DecimalField(max_digits=6, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)




