from decimal import Decimal
from django.db import transaction
from online_car_market.payroll.models import PayrollItem, PayrollLine, SalaryComponent
from online_car_market.hr.models import EmployeeSalary, OvertimeEntry
from online_car_market.payroll.services.tax import calculate_income_tax
from online_car_market.payroll.services.pension import calculate_pension
from online_car_market.payroll.services.allowances import split_taxable
from online_car_market.payroll.services.overtime import calculate_overtime_amount

TOTAL_MONTHLY_HOURS = Decimal("192")  # 8 * 6 * 4 (Ethiopian standard)

@transaction.atomic
def process_payroll_for_employee(employee, payroll_run):
    """
    Process payroll for a single employee and return a fully populated JSON
    with earnings, deductions, totals, and overtime summary.
    """

    salaries = EmployeeSalary.objects.select_related("component").filter(employee=employee)

    gross_earnings = Decimal("0.00")
    total_deductions = Decimal("0.00")
    taxable_income = Decimal("0.00")
    non_taxable_income = Decimal("0.00")
    pensionable_income = Decimal("0.00")

    # Create or get payroll item
    payroll_item, _ = PayrollItem.objects.get_or_create(
        payroll_run=payroll_run,
        employee=employee,
        defaults={
            "gross_earnings": Decimal("0.00"),
            "total_deductions": Decimal("0.00"),
            "net_salary": Decimal("0.00"),
        },
    )

    # Safe re-run
    payroll_item.payrollline_set.all().delete()

    earnings_list = []
    deductions_list = []

    # Base salary & allowances
    for salary in salaries:
        component = salary.component
        amount = salary.amount

        PayrollLine.objects.create(payroll_item=payroll_item, component=component, amount=amount)

        if component.component_type == SalaryComponent.EARNING:
            gross_earnings += amount
            earnings_list.append(
                {"name": component.name, "amount": str(amount)}
            )

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
            deductions_list.append(
                {"name": component.name, "amount": str(amount)}
            )

    # OVERTIME (1.5 / 1.75 / 2 / 2.5)
    overtime_summary = {
        "total_hours": Decimal("0.00"),
        "total_amount": Decimal("0.00"),
        "by_type": {},
    }

    overtime_component = SalaryComponent.objects.get(name__iexact="Overtime")

    overtime_entries = OvertimeEntry.objects.filter(employee=employee, payroll_run=payroll_run)

    basic_salary = salaries.filter(component__name__iexact="Basic Salary").first()

    if basic_salary:
        basic_salary_amount = basic_salary.amount

        for ot in overtime_entries:
            overtime_amount = calculate_overtime_amount(
                basic_salary=basic_salary_amount,
                total_hours_worked=TOTAL_MONTHLY_HOURS,
                overtime_hours=ot.hours,
                overtime_type=ot.overtime_type,
            )

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

            # 600 exemption applies
            split = split_taxable(overtime_amount)
            taxable_income += split["taxable"]
            non_taxable_income += split["non_taxable"]

            # ---- Overtime summary ----
            overtime_summary["total_hours"] += ot.hours
            overtime_summary["total_amount"] += overtime_amount

            if ot.overtime_type not in overtime_summary["by_type"]:
                overtime_summary["by_type"][ot.overtime_type] = {
                    "hours": Decimal("0.00"),
                    "amount": Decimal("0.00"),
                }

            overtime_summary["by_type"][ot.overtime_type]["hours"] += ot.hours
            overtime_summary["by_type"][ot.overtime_type]["amount"] += overtime_amount

    # Pension
    pension = calculate_pension(pensionable_income)
    employee_pension = pension["employee"]

    employee_pension_component = SalaryComponent.objects.get(
        name__iexact="Employee Pension"
    )

    PayrollLine.objects.create(
        payroll_item=payroll_item,
        component=employee_pension_component,
        amount=employee_pension,
    )

    total_deductions += employee_pension
    deductions_list.append(
        {"name": employee_pension_component.name, "amount": str(employee_pension)}
    )

    # Income Tax
    income_tax_amount = calculate_income_tax(taxable_income)

    income_tax_component = SalaryComponent.objects.get(name__iexact="Income Tax")

    PayrollLine.objects.create(payroll_item=payroll_item, component=income_tax_component, amount=income_tax_amount)

    total_deductions += income_tax_amount
    deductions_list.append(
        {"name": income_tax_component.name, "amount": str(income_tax_amount)}
    )

    # Final totals
    net_salary = gross_earnings - total_deductions

    payroll_item.gross_earnings = gross_earnings
    payroll_item.total_deductions = total_deductions
    payroll_item.net_salary = net_salary
    payroll_item.save()

    # Serialize overtime summary
    overtime_summary_serialized = {
        "total_hours": str(overtime_summary["total_hours"]),
        "total_amount": str(overtime_summary["total_amount"]),
        "by_type": {
            ot_type: {
                "hours": str(data["hours"]),
                "amount": str(data["amount"]),
            }
            for ot_type, data in overtime_summary["by_type"].items()
        },
    }

    return {
        "employee": employee.id,
        "gross_earnings": str(gross_earnings),
        "total_deductions": str(total_deductions),
        "net_salary": str(net_salary),
        "earnings": earnings_list,
        "deductions": deductions_list,
        "overtime_summary": overtime_summary_serialized,
    }
