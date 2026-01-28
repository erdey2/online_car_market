from decimal import Decimal
from django.db import transaction
from online_car_market.payroll.models import (
    Employee,
    EmployeeSalary,
    PayrollItem,
    PayrollLine,
    SalaryComponent,
)
from online_car_market.payroll.services.tax import calculate_income_tax
from online_car_market.payroll.services.pension import calculate_pension
from online_car_market.payroll.services.allowances import split_taxable


@transaction.atomic
def process_payroll_for_employee(employee, payroll_run):
    """
    Process payroll for a single employee and return a fully populated JSON
    with earnings, deductions, and totals.
    """
    salaries = EmployeeSalary.objects.select_related("component").filter(employee=employee)

    gross_earnings = Decimal("0.00")
    total_deductions = Decimal("0.00")
    taxable_income = Decimal("0.00")
    non_taxable_income = Decimal("0.00")
    pensionable_income = Decimal("0.00")

    # Create or get PayrollItem
    payroll_item, created = PayrollItem.objects.get_or_create(
        payroll_run=payroll_run,
        employee=employee,
        defaults={
            "gross_earnings": Decimal("0.00"),
            "total_deductions": Decimal("0.00"),
            "net_salary": Decimal("0.00"),
        }
    )

    # Clear old lines if re-running payroll
    payroll_item.payrollline_set.all().delete()

    earnings_list = []
    deductions_list = []

    # Process base salaries & allowances
    for salary in salaries:
        component = salary.component
        amount = salary.amount

        line_data = {
            "name": component.name,
            "amount": str(amount),
        }

        PayrollLine.objects.create(
            payroll_item=payroll_item,
            component=component,
            amount=amount,
        )

        if component.component_type == SalaryComponent.EARNING:
            gross_earnings += amount
            earnings_list.append(line_data)

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
            deductions_list.append(line_data)

    # Pension
    pension = calculate_pension(pensionable_income)
    employee_pension = pension["employee"]
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

    # Income Tax
    income_tax_amount = calculate_income_tax(taxable_income)
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

    # Final net salary
    net_salary = gross_earnings - total_deductions

    payroll_item.gross_earnings = gross_earnings
    payroll_item.total_deductions = total_deductions
    payroll_item.net_salary = net_salary
    payroll_item.save()

    # Return fully populated JSON for this employee
    return {
        "employee": employee.id,
        "gross_earnings": str(gross_earnings),
        "total_deductions": str(total_deductions),
        "net_salary": str(net_salary),
        "earnings": earnings_list,
        "deductions": deductions_list,
    }

