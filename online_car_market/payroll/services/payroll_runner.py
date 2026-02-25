from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Value
from django.db.models.functions import Cast, Coalesce
from decimal import Decimal
import calendar
from datetime import date
from online_car_market.hr.models import Employee
from online_car_market.payroll.models import PayrollRun, PayrollItem
from online_car_market.hr.models import EmployeeSalary, OvertimeEntry


@transaction.atomic
def run_payroll(payroll_run):

    # STATUS VALIDATION
    if payroll_run.status == "posted":
        raise ValidationError("Posted payroll cannot be modified")

    if payroll_run.status != "draft":
        raise ValueError("Payroll already processed")

    if PayrollRun.objects.filter(
        period=payroll_run.period,
        status__in=["approved", "posted"]
    ).exclude(id=payroll_run.id).exists():
        raise ValueError("Payroll already exists for this period")

    # DATE RANGE
    year = payroll_run.period.year
    month = payroll_run.period.month
    last_day = calendar.monthrange(year, month)[1]

    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    # ACTIVE EMPLOYEES
    employees = Employee.objects.filter(is_active=True).only("id")

    # OVERTIME AGGREGATION
    overtime_data = (
        OvertimeEntry.objects
        .filter(
            approved=True,
            date__range=(start_date, end_date)
        )
        .annotate(
            multiplier=Cast(
                "overtime_type",
                DecimalField(max_digits=4, decimal_places=2)
            )
        )
        .annotate(
            weighted_hours=ExpressionWrapper(
                F("hours") * F("multiplier"),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )
        .values("employee_id")
        .annotate(
            total_overtime=Coalesce(
                Sum("weighted_hours"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
    )

    overtime_map = {
        row["employee_id"]: row["total_overtime"]
        for row in overtime_data
    }

    # SALARY AGGREGATION
    salary_data = (
        EmployeeSalary.objects
        .values(
            "employee_id",
            "component__component_type"
        )
        .annotate(total=Sum("amount"))
    )

    earnings_map = {}
    deductions_map = {}

    for row in salary_data:
        emp_id = row["employee_id"]
        component_type = row["component__component_type"]
        total = row["total"]

        if component_type == "earning":
            earnings_map[emp_id] = total
        else:
            deductions_map[emp_id] = total

    # BUILD PAYROLL ITEMS
    payroll_items = []

    for emp in employees:

        base_earnings = earnings_map.get(emp.id, Decimal("0.00"))
        deductions = deductions_map.get(emp.id, Decimal("0.00"))
        overtime = overtime_map.get(emp.id, Decimal("0.00"))

        gross = base_earnings + overtime
        net = gross - deductions

        payroll_items.append(
            PayrollItem(
                payroll_run=payroll_run,
                employee=emp,
                gross_earnings=gross,
                total_deductions=deductions,
                net_salary=net,
            )
        )

    # Remove existing draft items (safe re-run)
    PayrollItem.objects.filter(payroll_run=payroll_run).delete()

    PayrollItem.objects.bulk_create(payroll_items)

    # UPDATE STATUS
    payroll_run.status = "approved"
    payroll_run.save(update_fields=["status"])

    return {
        "employees_processed": len(payroll_items)
    }
