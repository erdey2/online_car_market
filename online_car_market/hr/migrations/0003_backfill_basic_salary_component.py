from django.db import migrations


BASIC_SALARY_NAME = "Basic Salary"


def backfill_basic_salary(apps, schema_editor):
    Employee = apps.get_model("hr", "Employee")
    Contract = apps.get_model("hr", "Contract")
    SalaryComponent = apps.get_model("hr", "SalaryComponent")
    EmployeeSalary = apps.get_model("hr", "EmployeeSalary")

    basic_component, _ = SalaryComponent.objects.get_or_create(
        name=BASIC_SALARY_NAME,
        defaults={
            "component_type": "earning",
            "is_taxable": True,
            "is_pensionable": True,
            "is_system": True,
        },
    )

    active_contract_salary_by_employee = {}
    active_contracts = (
        Contract.objects
        .filter(status="active")
        .order_by("employee_id", "-created_at")
        .values("employee_id", "contract_salary")
    )
    for row in active_contracts:
        # Keep first row per employee because queryset is ordered by newest contract first.
        active_contract_salary_by_employee.setdefault(row["employee_id"], row["contract_salary"])

    for employee in Employee.objects.all().only("id", "salary"):
        source_amount = active_contract_salary_by_employee.get(employee.id)
        if source_amount is None:
            source_amount = employee.salary

        if source_amount is None:
            continue

        EmployeeSalary.objects.get_or_create(
            employee_id=employee.id,
            component_id=basic_component.id,
            defaults={"amount": source_amount},
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_basic_salary, noop_reverse),
    ]

