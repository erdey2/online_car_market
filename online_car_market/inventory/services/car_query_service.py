from rest_framework.exceptions import PermissionDenied
from online_car_market.inventory.models import Car
from django.db.models import Avg, Q, Max, Prefetch, Count
from rolepermissions.checkers import has_role
from ..models import CarImage
from online_car_market.bids.models import Bid

class CarQueryService:

    @staticmethod
    def base_queryset():
        return Car.objects.all()

    @staticmethod
    def for_list():
        return (
            Car.objects
            .select_related("dealer", "dealer__profile", "make_ref", "model_ref")
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=CarImage.objects.only("id", "image", "is_featured")
                )
            )
            .annotate(
                dealer_avg=Avg("dealer__ratings__rating"),
            )
            .order_by("-priority", "-created_at")
        )

    @staticmethod
    def for_detail():
        return (
            Car.objects
            .select_related(
                "dealer",
                "dealer__profile",
                "broker",
                "broker__profile",
                "posted_by",
                "make_ref",
                "model_ref",
            )
            .prefetch_related(
                "images",
                Prefetch(
                    "bids",
                    queryset=Bid.objects.select_related("user")
                    .only("id", "amount", "user_id", "created_at")
                    .order_by("-amount")[:10]  # only top 10 bids
                )
            )
            .annotate(
                bid_count=Count("bids", distinct=True),
                highest_bid=Max("bids__amount"),
                dealer_avg=Avg("dealer__ratings__rating"),
            )
        )

    @staticmethod
    def get_visible_cars_for_user(user, queryset):
        if not user.is_authenticated:
            return queryset.filter(verification_status="verified")

        if has_role(user, ["super_admin", "admin"]):
            return queryset

        if has_role(user, "dealer"):
            return queryset.filter(
                Q(dealer__profile__user=user) |
                Q(verification_status="verified")
            )

        if has_role(user, "seller"):
            return queryset.filter(dealer__dealerstaff__user=user)

        if has_role(user, "broker"):
            return queryset.filter(
                Q(broker__profile__user=user) |
                Q(verification_status="verified")
            )

        return queryset.filter(verification_status="verified")

    @staticmethod
    def get_verification_cars_for_user(user, verification_status=None):
        qs = CarQueryService.base_queryset()

        # Role-based visibility
        if has_role(user, ["super_admin", "admin"]):
            pass

        elif has_role(user, "dealer"):
            qs = qs.filter(dealer__profile__user=user)

        elif has_role(user, "broker"):
            qs = qs.filter(broker__profile__user=user)

        else:
            raise PermissionDenied(
                "You are not allowed to view verification records."
            )

        # Optional status filtering
        if verification_status:
            qs = qs.filter(verification_status=verification_status)

        return qs.order_by("-created_at")

