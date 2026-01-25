from django.db import transaction
from online_car_market.payroll.models import Employee, PayrollItem
from online_car_market.payroll.services.payroll_processor import process_payroll_for_employee

@transaction.atomic
def run_payroll(payroll_run):
    if payroll_run.status != "draft":
        raise ValueError("Payroll already processed")

    if PayrollItem.objects.filter(payroll_run=payroll_run).exists():
        raise ValueError("Payroll items already exist")

    employees = Employee.objects.filter(is_active=True)

    for employee in employees:
        process_payroll_for_employee(employee, payroll_run)

    payroll_run.status = "approved"
    payroll_run.save()
