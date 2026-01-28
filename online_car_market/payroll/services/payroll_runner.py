from django.db import transaction
from django.core.exceptions import ValidationError
from online_car_market.payroll.models import Employee, PayrollRun
from online_car_market.payroll.services.payroll_processor import process_payroll_for_employee

@transaction.atomic
def run_payroll(payroll_run):
    # 🔒 Prevent modifying posted payroll
    if payroll_run.status == "posted":
        raise ValidationError("Posted payroll cannot be modified")

    if payroll_run.status != "draft":
        raise ValueError("Payroll already processed")

    if PayrollRun.objects.filter(
        period=payroll_run.period,
        status__in=["approved", "posted"]
    ).exclude(id=payroll_run.id).exists():
        raise ValueError("Payroll already exists for this period")

    results = []

    for employee in Employee.objects.filter(is_active=True):
        result = process_payroll_for_employee(employee, payroll_run)

        if not result["earnings"]:
            raise ValueError(
                f"Payroll failed for employee {employee.id}. No earnings generated."
            )

        results.append(result)

    payroll_run.status = "approved"
    payroll_run.save()

    return results



