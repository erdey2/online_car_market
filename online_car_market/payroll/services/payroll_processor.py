from decimal import Decimal
from django.db import transaction

from online_car_market.payroll.models import PayrollItem, PayrollLine, SalaryComponent
from online_car_market.hr.models import EmployeeSalary, OvertimeEntry
from online_car_market.payroll.services.tax import calculate_income_tax
from online_car_market.payroll.services.pension import calculate_pension
from online_car_market.payroll.services.allowances import split_taxable
from online_car_market.payroll.services.overtime import calculate_overtime_amount
from online_car_market.hr.services.attendance_service import AttendanceService


@transaction.atomic
def process_payroll_for_employee(employee, payroll_run, year, month):
    """
    Process payroll for a single employee using optimized attendance analytics.
    """
    salaries = EmployeeSalary.objects.select_related("component").filter(employee=employee)

    gross_earnings = Decimal("0.00")
    total_deductions = Decimal("0.00")
    taxable_income = Decimal("0.00")
    non_taxable_income = Decimal("0.00")
    pensionable_income = Decimal("0.00")

    # Attendance Summary
    attendance_data = AttendanceService.monthly_employee_summary(
        year=year,
        month=month,
        employee=employee,
    )

    worked_hours = attendance_data["total_actual_hours"]
    working_days = attendance_data["total_working_days"]

    expected_hours = (
        Decimal(working_days)
        * AttendanceService.STANDARD_DAILY_HOURS
    )

    # Payroll Item
    payroll_item, _ = PayrollItem.objects.get_or_create(
        payroll_run=payroll_run,
        employee=employee,
        defaults={
            "gross_earnings": Decimal("0.00"),
            "total_deductions": Decimal("0.00"),
            "net_salary": Decimal("0.00"),
        },
    )

    payroll_item.payrollline_set.all().delete()

    earnings_list = []
    deductions_list = []

    # Base Salary & Allowances
    for salary in salaries:
        component = salary.component
        amount = salary.amount

        PayrollLine.objects.create(
            payroll_item=payroll_item,
            component=component,
            amount=amount,
        )

        if component.component_type == SalaryComponent.EARNING:
            gross_earnings += amount
            earnings_list.append({"name": component.name, "amount": str(amount)})

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
            deductions_list.append({"name": component.name, "amount": str(amount)})

    # OVERTIME
    overtime_summary = {
        "total_hours": Decimal("0.00"),
        "total_amount": Decimal("0.00"),
        "by_type": {},
    }

    try:
        overtime_component = SalaryComponent.objects.get(name__iexact="Overtime")
    except SalaryComponent.DoesNotExist:
        overtime_component = None

    overtime_entries = OvertimeEntry.objects.filter(
        employee=employee,
        payroll_run=payroll_run,
    )

    basic_salary = salaries.filter(
        component__name__iexact="Basic Salary"
    ).first()

    basic_salary_amount = basic_salary.amount if basic_salary else Decimal("0.00")

    if expected_hours <= 0:
        raise ValueError("Expected hours cannot be zero for payroll calculation.")

    for ot in overtime_entries:

        overtime_hours = (
            ot.hours if isinstance(ot.hours, Decimal)
            else Decimal(str(ot.hours))
        )

        overtime_amount = calculate_overtime_amount(
            basic_salary=basic_salary_amount,
            expected_hours=expected_hours,
            overtime_hours=overtime_hours,
            overtime_type=ot.overtime_type,
        )

        if overtime_component:
            PayrollLine.objects.create(
                payroll_item=payroll_item,
                component=overtime_component,
                amount=overtime_amount,
            )

        gross_earnings += overtime_amount

        earnings_list.append({
            "name": f"Overtime ({ot.overtime_type})",
            "amount": str(overtime_amount),
        })

        split = split_taxable(overtime_amount)
        taxable_income += split["taxable"]
        non_taxable_income += split["non_taxable"]

        overtime_summary["total_hours"] += overtime_hours
        overtime_summary["total_amount"] += overtime_amount

        overtime_summary["by_type"].setdefault(
            ot.overtime_type,
            {"hours": Decimal("0.00"), "amount": Decimal("0.00")},
        )

        overtime_summary["by_type"][ot.overtime_type]["hours"] += overtime_hours
        overtime_summary["by_type"][ot.overtime_type]["amount"] += overtime_amount

    # Pension
    pension = calculate_pension(pensionable_income)
    employee_pension = pension["employee"]

    try:
        employee_pension_component = SalaryComponent.objects.get(name__iexact="Employee Pension")

        PayrollLine.objects.create(
            payroll_item=payroll_item,
            component=employee_pension_component,
            amount=employee_pension,
        )

        total_deductions += employee_pension
        deductions_list.append({
            "name": employee_pension_component.name,
            "amount": str(employee_pension),
        })

    except SalaryComponent.DoesNotExist:
        pass

    # Income Tax
    income_tax_amount = calculate_income_tax(taxable_income)

    try:
        income_tax_component = SalaryComponent.objects.get(name__iexact="Income Tax")

        PayrollLine.objects.create(
            payroll_item=payroll_item,
            component=income_tax_component,
            amount=income_tax_amount,
        )

        total_deductions += income_tax_amount
        deductions_list.append({
            "name": income_tax_component.name,
            "amount": str(income_tax_amount),
        })

    except SalaryComponent.DoesNotExist:
        pass

    # Final Totals
    net_salary = gross_earnings - total_deductions

    payroll_item.gross_earnings = gross_earnings
    payroll_item.total_deductions = total_deductions
    payroll_item.net_salary = net_salary
    payroll_item.save()

    return {
        "employee": employee.id,
        "gross_earnings": str(gross_earnings),
        "total_deductions": str(total_deductions),
        "net_salary": str(net_salary),
        "worked_hours": str(worked_hours),
        "working_days": working_days,
        "attendance_summary": attendance_data,
    }
