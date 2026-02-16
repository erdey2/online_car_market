from online_car_market.inventory.models import Car
from django.db.models import Avg, Q
from rolepermissions.checkers import has_role

class CarQueryService:

    @staticmethod
    def base_queryset():
        return (
            Car.objects
            .select_related(
                "dealer",
                "dealer__profile",
                "broker",
                "broker__profile",
                "posted_by",
            )
            .prefetch_related("images", "bids", "ratings")
        )

    @staticmethod
    def annotate_for_listing(queryset):
        return queryset.annotate(
            dealer_avg=Avg("dealer__ratings__rating"),
            broker_avg=Avg("broker__ratings__rating"),
        ).order_by("-priority", "-created_at")

    @staticmethod
    def get_visible_cars_for_user(user):
        qs = CarQueryService.base_queryset()

        if not user.is_authenticated:
            return qs.filter(verification_status="verified")

        if has_role(user, ["super_admin", "admin"]):
            return qs

        if has_role(user, "dealer"):
            return qs.filter(
                Q(dealer__profile__user=user) |
                Q(verification_status="verified")
            )

        if has_role(user, "seller"):
            return qs.filter(dealer__dealerstaff__user=user)

        if has_role(user, "broker"):
            return qs.filter(
                Q(broker__profile__user=user) |
                Q(verification_status="verified")
            )

        return qs.filter(verification_status="verified")
