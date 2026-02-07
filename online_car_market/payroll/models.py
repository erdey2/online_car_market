from django.db import models
from django.contrib.auth import get_user_model
from online_car_market.hr.models import SalaryComponent, Employee

User = get_user_model()

class PayrollRun(models.Model):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"

    STATUS_CHOICES = [(DRAFT, "Draft"), (APPROVED, "Approved"), (POSTED, "Posted")]
    period = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["period"],
                name="unique_payroll_per_period"
            )
        ]

    def is_editable(self):
        return self.status != self.POSTED

class PayrollItem(models.Model):
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name="items"
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="payroll_items"
    )
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
    payroll_item = models.ForeignKey(PayrollItem, on_delete=models.CASCADE, related_name="lines")
    component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)





