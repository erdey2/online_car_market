from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone
from django.db import transaction
from online_car_market.dealers.models import DealerStaff
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

        if (
            new_status == Lead.LeadStatus.CLOSED
            and old_status != Lead.LeadStatus.CLOSED
        ):
            lead.closed_at = timezone.now()
            lead.closed_by = user

            if lead.car and lead.car.status == "available":
                lead.car.status = "sold"
                lead.car.sold_at = timezone.now()
                lead.car.save()

        if (
            old_status == Lead.LeadStatus.CLOSED
            and new_status != Lead.LeadStatus.CLOSED
        ):
            lead.closed_at = None
            lead.closed_by = None

        lead.save()
        return lead

    @staticmethod
    def _filter_for_user(qs, user):
        """
        Shared role-based filtering.
        """

        if user.is_superuser:
            return qs

        if hasattr(user, "dealer"):
            return qs.filter(car__dealer=user.dealer)

        if hasattr(user, "broker"):
            return qs.filter(car__broker=user.broker)

        staff_assignment = (
            DealerStaff.objects
            .filter(user=user)
            .select_related("dealer")
            .first()
        )

        if staff_assignment:
            return qs.filter(
                car__dealer=staff_assignment.dealer
            )

        return qs.filter(buyer=user)

    @staticmethod
    def total_leads(user=None):
        qs = Lead.objects.select_related(
            "car",
            "buyer"
        ).all()

        if user:
            qs = LeadService._filter_for_user(qs, user)

        return qs.count()

    @staticmethod
    def leads_by_status(user=None):
        qs = Lead.objects.select_related(
            "car",
            "buyer"
        ).all()

        if user:
            qs = LeadService._filter_for_user(qs, user)

        return qs.values(
            "status"
        ).annotate(
            count=Count("id")
        )

    @staticmethod
    def conversion_rate(user=None):
        qs = Lead.objects.select_related(
            "car",
            "buyer"
        ).all()

        if user:
            qs = LeadService._filter_for_user(qs, user)

        total = qs.count()
        closed = qs.filter(
            status=Lead.LeadStatus.CLOSED
        ).count()

        return (closed / total * 100) if total > 0 else 0


    @staticmethod
    def avg_time_to_close(user=None):
        qs = Lead.objects.filter(
            status=Lead.LeadStatus.CLOSED
        ).select_related(
            "car",
            "buyer"
        )

        if user:
            qs = LeadService._filter_for_user(qs, user)

        avg_time = qs.annotate(
            duration=ExpressionWrapper(
                F("closed_at") - F("created_at"),
                output_field=DurationField(),
            )
        ).aggregate(
            avg_duration=Avg("duration")
        )["avg_duration"]

        return avg_time
