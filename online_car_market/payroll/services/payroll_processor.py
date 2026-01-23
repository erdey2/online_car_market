from decimal import Decimal
from online_car_market.payroll.models import (
    Employee,
    EmployeeSalary,
    PayrollItem,
    PayrollLine,
    SalaryComponent
)
from online_car_market.payroll.services.tax import calculate_income_tax
from online_car_market.payroll.services.pension import calculate_pension

def process_payroll_for_employee(employee, payroll_run):
    salaries = EmployeeSalary.objects.select_related("component").filter(
        employee=employee
    )

    gross_earnings = Decimal("0.00")
    total_deductions = Decimal("0.00")
    taxable_income = Decimal("0.00")
    pensionable_income = Decimal("0.00")

    payroll_item = PayrollItem.objects.create(
        payroll_run=payroll_run,
        employee=employee,
        gross_earnings=0,
        total_deductions=0,
        net_salary=0,
    )

    # 1️⃣ Process earnings & deductions
    for salary in salaries:
        component = salary.component
        amount = salary.amount

        PayrollLine.objects.create(
            payroll_item=payroll_item,
            component=component,
            amount=amount
        )

        if component.component_type == SalaryComponent.EARNING:
            gross_earnings += amount

            if component.is_taxable:
                taxable_income += amount

            if component.is_pensionable:
                pensionable_income += amount

        else:  # deduction
            total_deductions += amount

    pension = calculate_pension(pensionable_income)

    employee_pension = pension["employee"]
    employer_pension = pension["employer"]

    # Employee pension is a deduction
    total_deductions += employee_pension

    PayrollLine.objects.create(
        payroll_item=payroll_item,
        component=SalaryComponent.objects.get(name="Employee Pension"),
        amount=employee_pension
    )

    income_tax = Decimal(
        calculate_income_tax(float(taxable_income))
    )

    total_deductions += income_tax

    PayrollLine.objects.create(
        payroll_item=payroll_item,
        component=SalaryComponent.objects.get(name="Income Tax"),
        amount=income_tax
    )

    net_salary = gross_earnings - total_deductions

    payroll_item.gross_earnings = gross_earnings
    payroll_item.total_deductions = total_deductions
    payroll_item.net_salary = net_salary
    payroll_item.save()

    return payroll_item

def run_payroll(payroll_run):
    employees = Employee.objects.filter(is_active=True)

    for employee in employees:
        process_payroll_for_employee(employee, payroll_run)

    payroll_run.status = "approved"
    payroll_run.save()






