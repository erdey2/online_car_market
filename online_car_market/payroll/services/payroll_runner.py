from decimal import Decimal
import calendar
from datetime import date, timedelta
from django.db import transaction
from django.core.exceptions import ValidationError

from online_car_market.hr.models import Employee, EmployeeSalary, OvertimeEntry
from online_car_market.payroll.models import PayrollRun, PayrollItem, PayrollLine, SalaryComponent
from online_car_market.payroll.services.allowances import split_taxable
from online_car_market.payroll.services.overtime import calculate_overtime_amount
from online_car_market.payroll.services.pension import calculate_pension
from online_car_market.payroll.services.tax import calculate_income_tax


def _get_system_component(name, component_type, *, is_taxable=False, is_pensionable=False):
    component, _ = SalaryComponent.objects.get_or_create(
        name=name,
        defaults={
            "component_type": component_type,
            "is_taxable": is_taxable,
            "is_pensionable": is_pensionable,
            "is_system": True,
        },
    )
    return component


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

    PayrollItem.objects.filter(payroll_run=payroll_run).delete()

    # DATE RANGE
    year = payroll_run.period.year
    month = payroll_run.period.month
    last_day = calendar.monthrange(year, month)[1]

    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    # ACTIVE EMPLOYEES
    employees = Employee.objects.filter(is_active=True).only("id")

    overtime_component = _get_system_component(
        "Overtime",
        SalaryComponent.EARNING,
        is_taxable=True,
        is_pensionable=False,
    )
    employee_pension_component = _get_system_component(
        "Employee Pension",
        SalaryComponent.DEDUCTION,
        is_taxable=False,
        is_pensionable=False,
    )
    income_tax_component = _get_system_component(
        "Income Tax",
        SalaryComponent.DEDUCTION,
        is_taxable=False,
        is_pensionable=False,
    )

    processed = []

    for emp in employees:
        salaries = EmployeeSalary.objects.select_related("component").filter(employee=emp)

        gross_earnings = Decimal("0.00")
        total_deductions = Decimal("0.00")
        taxable_income = Decimal("0.00")
        non_taxable_income = Decimal("0.00")
        pensionable_income = Decimal("0.00")

        payroll_item = PayrollItem(
            payroll_run=payroll_run,
            employee=emp,
            gross_earnings=Decimal("0.00"),
            total_deductions=Decimal("0.00"),
            net_salary=Decimal("0.00"),
        )

        line_items = []

        basic_salary = salaries.filter(component__name__iexact="Basic Salary").first()
        basic_salary_amount = basic_salary.amount if basic_salary else Decimal("0.00")

        total_days_in_month = (end_date - start_date).days + 1
        sundays = sum(
            1
            for i in range(total_days_in_month)
            if (start_date + timedelta(days=i)).weekday() == 6
        )
        working_days = total_days_in_month - sundays
        expected_hours = Decimal(working_days) * Decimal("8.0")

        for salary in salaries:
            component = salary.component
            amount = salary.amount

            line_items.append(
                PayrollLine(
                    payroll_item=payroll_item,
                    component=component,
                    amount=amount,
                )
            )

            if component.component_type == SalaryComponent.EARNING:
                gross_earnings += amount

                if component.is_taxable:
                    split = split_taxable(amount)
                    taxable_income += split["taxable"]
                    non_taxable_income += split["non_taxable"]
                else:
                    non_taxable_income += amount

                if component.is_pensionable:
                    pensionable_income += amount
            else:
                total_deductions += amount

        overtime_entries = OvertimeEntry.objects.filter(
            employee=emp,
            approved=True,
            date__range=(start_date, end_date),
        ).order_by("date", "id")

        for ot in overtime_entries:
            overtime_hours = ot.hours if isinstance(ot.hours, Decimal) else Decimal(str(ot.hours))
            overtime_amount = calculate_overtime_amount(
                basic_salary=basic_salary_amount,
                total_hours_worked=expected_hours,
                overtime_hours=overtime_hours,
                overtime_type=ot.overtime_type,
            )

            line_items.append(
                PayrollLine(
                    payroll_item=payroll_item,
                    component=overtime_component,
                    amount=overtime_amount,
                )
            )

            gross_earnings += overtime_amount
            split = split_taxable(overtime_amount)
            taxable_income += split["taxable"]
            non_taxable_income += split["non_taxable"]

        employee_pension = calculate_pension(pensionable_income)["employee"]
        if employee_pension > 0:
            line_items.append(
                PayrollLine(
                    payroll_item=payroll_item,
                    component=employee_pension_component,
                    amount=employee_pension,
                )
            )
            total_deductions += employee_pension

        income_tax_amount = calculate_income_tax(taxable_income)
        if income_tax_amount > 0:
            line_items.append(
                PayrollLine(
                    payroll_item=payroll_item,
                    component=income_tax_component,
                    amount=income_tax_amount,
                )
            )
            total_deductions += income_tax_amount

        net_salary = gross_earnings - total_deductions

        payroll_item.gross_earnings = gross_earnings
        payroll_item.total_deductions = total_deductions
        payroll_item.net_salary = net_salary

        payroll_item.save()
        PayrollLine.objects.bulk_create(line_items)

        processed.append({
            "employee": emp.pk,
            "gross_earnings": str(gross_earnings),
            "total_deductions": str(total_deductions),
            "net_salary": str(net_salary),
            "line_count": len(line_items),
        })

    return {
        "employees_processed": len(processed),
        "items": processed,
    }
