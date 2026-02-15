from django.utils import timezone
from django.db import transaction
from ..models import Lead


class LeadService:

    @staticmethod
    @transaction.atomic
    def create_lead(*, car, name, contact, buyer=None):
        return Lead.objects.create(
            car=car,
            name=name,
            contact=contact,
            buyer=buyer
        )

    @staticmethod
    @transaction.atomic
    def update_status(*, lead, new_status, user):
        old_status = lead.status
        lead.status = new_status

        # Handle closing logic
        if new_status == Lead.LeadStatus.CLOSED and old_status != Lead.LeadStatus.CLOSED:
            lead.closed_at = timezone.now()
            lead.closed_by = user

            if lead.car and lead.car.status == "available":
                lead.car.status = "sold"
                lead.car.sold_at = timezone.now()
                lead.car.save()

        if old_status == Lead.LeadStatus.CLOSED and new_status != Lead.LeadStatus.CLOSED:
            lead.closed_at = None
            lead.closed_by = None

        lead.save()
        return lead
