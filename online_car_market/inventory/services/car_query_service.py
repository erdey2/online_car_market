from django.db.models import Avg, Count, FloatField, Max, Prefetch, Q
from django.db.models.functions import Coalesce
from rest_framework.exceptions import PermissionDenied
from rolepermissions.checkers import has_role
from online_car_market.bids.models import Bid
from online_car_market.inspection.models import Inspection
from online_car_market.inventory.models import Car, CarImage


class CarQueryService:

    @staticmethod
    def base_queryset():
        return Car.objects.all()

    @staticmethod
    def _with_dealer_rating(queryset):
        return queryset.annotate(
            dealer_avg=Coalesce(
                Avg("dealer__ratings__rating"),
                0.0,
                output_field=FloatField(),
            )
        )

    @staticmethod
    def _prefetch_featured_image(queryset):
        featured_images = CarImage.objects.filter(
            is_featured=True
        ).only(
            "id",
            "image",
            "is_featured",
        )

        return queryset.prefetch_related(
            Prefetch(
                "images",
                queryset=featured_images,
                to_attr="featured_images",
            )
        )

    @staticmethod
    def for_list():
        queryset = (
            CarQueryService.base_queryset()
            .select_related(
                "dealer",
                "dealer__profile",
                "make_ref",
                "model_ref",
            )
            .order_by(
                "-priority",
                "-created_at",
            )
        )

        queryset = CarQueryService._prefetch_featured_image(
            queryset
        )

        return CarQueryService._with_dealer_rating(
            queryset
        )

    @staticmethod
    def for_detail():

        all_images = CarImage.objects.only(
            "id",
            "image",
            "is_featured",
        )

        top_bids = (
            Bid.objects
            .select_related("user")
            .only(
                "id",
                "amount",
                "user_id",
                "created_at",
            )
            .order_by("-amount")[:10]
        )

        inspections = (
            Inspection.objects
            .filter(status="verified")
            .select_related("verified_by")
            .order_by("-verified_at")
        )

        queryset = (
            CarQueryService.base_queryset()
            .select_related(
                "dealer",
                "dealer__profile",
                "dealer__profile__user",
                "broker",
                "broker__profile",
                "broker__profile__user",
                "posted_by",
                "make_ref",
                "model_ref",
            )
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=all_images,
                ),
                Prefetch(
                    "bids",
                    queryset=top_bids,
                    to_attr="top_bids",
                ),
                Prefetch(
                    "inspections",
                    queryset=inspections,
                    to_attr="verified_inspections",
                ),
            )
            .annotate(
                bid_count=Count(
                    "bids",
                    distinct=True,
                ),
                highest_bid=Max(
                    "bids__amount",
                ),
            )
        )

        return CarQueryService._with_dealer_rating(
            queryset
        )

    @staticmethod
    def get_visible_cars_for_user(user, queryset):
        """
        Apply role-based visibility.
        Prefetching should already be applied before this method.
        """

        if not user.is_authenticated:
            return queryset.filter(
                verification_status="verified"
            )

        if has_role(
            user,
            [
                "super_admin",
                "admin",
            ],
        ):
            return queryset

        if has_role(user, "dealer"):
            return queryset.filter(
                Q(
                    dealer__profile__user=user
                )
                | Q(
                    verification_status="verified"
                )
            )

        if has_role(user, "seller"):
            return queryset.filter(
                dealer__dealerstaff__user=user
            )

        if has_role(user, "broker"):
            return queryset.filter(
                Q(
                    broker__profile__user=user
                )
                | Q(
                    verification_status="verified"
                )
            )

        return queryset.filter(
            verification_status="verified"
        )

    @staticmethod
    def get_verification_cars_for_user(
        user,
        verification_status=None,
    ):
        queryset = CarQueryService.base_queryset()

        if has_role(
            user,
            [
                "super_admin",
                "admin",
            ],
        ):
            pass

        elif has_role(user, "dealer"):
            queryset = queryset.filter(
                dealer__profile__user=user
            )

        elif has_role(user, "broker"):
            queryset = queryset.filter(
                broker__profile__user=user
            )

        else:
            raise PermissionDenied(
                "You are not allowed to view verification records."
            )

        if verification_status:
            queryset = queryset.filter(
                verification_status=verification_status
            )

        return (
            queryset
            .select_related(
                "dealer",
                "broker__profile",
                "posted_by",
            )
            .only(
                "id",
                "make",
                "model",
                "year",
                "price",
                "sale_type",
                "verification_status",
                "priority",
                "created_at",
                "dealer__company_name",
                "broker__profile__first_name",
                "broker__profile__last_name",
                "posted_by__email",
            )
            .order_by("-created_at")
        )
