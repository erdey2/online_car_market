from django.core.management.base import BaseCommand
from online_car_market.payroll.models import SalaryComponent

class Command(BaseCommand):
    help = "Seed system salary components"

    def handle(self, *args, **options):
        components = [
            {
                "name": "Income Tax",
                "component_type": SalaryComponent.DEDUCTION,
                "is_taxable": False,
                "is_pensionable": False,
                "is_system": True,
            },
            {
                "name": "Employee Pension",
                "component_type": SalaryComponent.DEDUCTION,
                "is_taxable": False,
                "is_pensionable": False,
                "is_system": True,
            },
            {
                "name": "Employer Pension",
                "component_type": SalaryComponent.EARNING,
                "is_taxable": False,
                "is_pensionable": False,
                "is_system": True,
            },
        ]

        for comp in components:
            obj, created = SalaryComponent.objects.get_or_create(
                name=comp["name"],
                defaults=comp,
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created {obj.name}"))
            else:
                self.stdout.write(f"{obj.name} already exists")
