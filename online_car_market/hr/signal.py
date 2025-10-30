from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Contract, Employee

@receiver([post_save, post_delete], sender=Contract)
def sync_employee_salary(sender, instance, **kwargs):
    employee = instance.employee
    active_contract = employee.contracts.filter(status='active').first()
    new_salary = active_contract.salary if active_contract else None
    if employee.salary != new_salary:
        employee.salary = new_salary
        employee.save(update_fields=['salary'])
