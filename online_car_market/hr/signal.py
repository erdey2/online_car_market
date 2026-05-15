from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Contract, SalaryComponent, EmployeeSalary


BASIC_SALARY_COMPONENT = "Basic Salary"

@receiver([post_save, post_delete], sender=Contract)
def sync_employee_basic_salary_component(sender, instance, **kwargs):
    employee = instance.employee
    active_contract = employee.contracts.filter(status='active').order_by('-created_at').first()

    if not active_contract:
        return

    basic_component, _ = SalaryComponent.objects.get_or_create(
        name=BASIC_SALARY_COMPONENT,
        defaults={
            "component_type": SalaryComponent.EARNING,
            "is_taxable": True,
            "is_pensionable": True,
            "is_system": True,
        },
    )

    EmployeeSalary.objects.update_or_create(
        employee=employee,
        component=basic_component,
        defaults={"amount": active_contract.contract_salary},
    )
