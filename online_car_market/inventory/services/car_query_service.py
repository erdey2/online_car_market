from django.db.models import Prefetch, Max, Count, OuterRef, Subquery, FloatField
from django.db.models import Q, Avg
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
        Optimized list view:
        """
        images_qs = CarImage.objects.only("id", "image", "is_featured")
        prefetch_images = Prefetch("images", queryset=images_qs, to_attr="featured_images")

        return (
            Car.objects
            .select_related("dealer", "dealer__profile", "make_ref", "model_ref")
            .prefetch_related(prefetch_images)
            .annotate(
                dealer_avg=Coalesce(
                    Avg("dealer__ratings__rating"),
                    0.0,
                    output_field=FloatField()
                )
            )
            .order_by("-priority", "-created_at")
        )

    @staticmethod
    def for_detail():
        """
        Optimized detail view:
        """
        # Prefetch top 10 bids per car
        top_bids_qs = (
            Bid.objects
            .select_related("user")
            .only("id", "amount", "user_id", "created_at")
            .order_by("-amount")[:10]  # top 10 bids
        )

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
                Prefetch("bids", queryset=top_bids_qs, to_attr="top_bids")  # top 10 bids stored in `car.top_bids`
            )
            .annotate(
                bid_count=Count("bids", distinct=True),
                highest_bid=Max("bids__amount"),
                dealer_avg=Coalesce(
                    Avg("dealer__ratings__rating"),
                    0.0,
                    output_field=FloatField()
                ),
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
