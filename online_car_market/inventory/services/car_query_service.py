from django.db.models import Prefetch, Max, Count, OuterRef, Subquery
from django.db.models import Q
from django.db.models.functions import Coalesce
from rolepermissions.checkers import has_role
from rest_framework.exceptions import PermissionDenied
from online_car_market.inventory.models import Car
from ..models import CarImage
from online_car_market.bids.models import Bid

class CarQueryService:

    @staticmethod
    def base_queryset():
        return Car.objects.all()

    @staticmethod
    def for_list():
        """
        Optimized list view: fetch cars with dealer info and featured images.
        """
        return (
            Car.objects
            .select_related(
                "dealer",
                "dealer__profile",
                "make_ref",
                "model_ref",
            )
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=CarImage.objects.only("id", "image", "is_featured").filter(is_featured=True),
                    to_attr="featured_images"  # avoids repeated access hits
                )
            )
            .annotate(
                dealer_avg=Coalesce("dealer__cached_avg_rating", 0),
            )
            .only("id", "title", "price", "priority", "verification_status", "dealer_id", "make_ref_id", "model_ref_id")
            .order_by("-priority", "-created_at")
        )

    @staticmethod
    def for_detail():
        """
        Optimized detail view: fetch top 10 bids per car using Subquery.
        """
        # Subquery for top 10 bid IDs per car
        top_bids_subquery = Bid.objects.filter(car=OuterRef("pk")).order_by("-amount").values("pk")[:10]

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
            )
            .annotate(
                bid_count=Count("bids", distinct=True),
                highest_bid=Max("bids__amount"),
                dealer_avg=Coalesce("dealer__cached_avg_rating", 0),
                top_bid_id=Subquery(top_bids_subquery)
            )
        )

    @staticmethod
    def get_visible_cars_for_user(user, queryset):
        if not user.is_authenticated:
            return queryset.filter(verification_status="verified")

        if has_role(user, ["super_admin", "admin"]):
            return queryset

        if has_role(user, "dealer"):
            dealer_profile_id = getattr(user, "dealer_profile_id", None)
            return queryset.filter(
                Q(dealer__profile_id=dealer_profile_id) |
                Q(verification_status="verified")
            )

        if has_role(user, "seller"):
            return queryset.filter(dealer__dealerstaff__user_id=user.id)

        if has_role(user, "broker"):
            broker_profile_id = getattr(user, "broker_profile_id", None)
            return queryset.filter(
                Q(broker__profile_id=broker_profile_id) |
                Q(verification_status="verified")
            )

        return queryset.filter(verification_status="verified")

    @staticmethod
    def get_verification_cars_for_user(user, verification_status=None):
        qs = CarQueryService.base_queryset()

        if has_role(user, ["super_admin", "admin"]):
            pass
        elif has_role(user, "dealer"):
            qs = qs.filter(dealer__profile_id=getattr(user, "dealer_profile_id", None))
        elif has_role(user, "broker"):
            qs = qs.filter(broker__profile_id=getattr(user, "broker_profile_id", None))
        else:
            raise PermissionDenied(
                "You are not allowed to view verification records."
            )

        if verification_status:
            qs = qs.filter(verification_status=verification_status)

        return qs.order_by("-created_at")
