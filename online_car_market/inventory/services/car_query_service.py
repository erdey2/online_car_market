from django.db.models import Avg, Max, Count, FloatField, Prefetch, Q
from django.db.models.functions import Coalesce
from rest_framework.exceptions import PermissionDenied
from online_car_market.inventory.models import Car, CarImage
from online_car_market.bids.models import Bid
from rolepermissions.checkers import has_role

class CarQueryService:

    @staticmethod
    def base_queryset():
        """Return base queryset for Car."""
        return Car.objects.all()

    @staticmethod
    def _prefetch_featured_image(queryset):
        """
        Prefetch only the featured image for list view.
        Stored in `featured_images` attribute.
        """
        featured_qs = CarImage.objects.filter(is_featured=True).only("id", "image", "is_featured")
        return queryset.prefetch_related(Prefetch("images", queryset=featured_qs, to_attr="featured_images"))

    @staticmethod
    def _prefetch_all_images(queryset):
        """
        Prefetch all images for detail view.
        Stored in `images` attribute.
        """
        all_images_qs = CarImage.objects.all().only("id", "image", "is_featured")
        return queryset.prefetch_related(Prefetch("images", queryset=all_images_qs))

    @staticmethod
    def for_list():
        """
        List view optimized:
        - Only featured image
        - Annotate dealer average rating
        - Order by priority and creation date
        """
        qs = Car.objects.select_related(
            "dealer", "dealer__profile", "make_ref", "model_ref"
        )
        qs = CarQueryService._prefetch_featured_image(qs)
        qs = qs.annotate(
            dealer_avg=Coalesce(
                Avg("dealer__ratings__rating"),
                0.0,
                output_field=FloatField()
            )
        ).order_by("-priority", "-created_at")
        return qs

    @staticmethod
    def for_detail():
        """
        Detail view optimized:
        - Prefetch top 10 bids
        - Prefetch all images
        - Annotate bid count, highest bid, dealer average
        """
        # Prefetch top 10 bids per car
        top_bids_qs = (
            Bid.objects.select_related("user")
            .only("id", "amount", "user_id", "created_at")
            .order_by("-amount")[:10]
        )

        qs = Car.objects.select_related(
            "dealer",
            "dealer__profile",
            "broker",
            "broker__profile",
            "posted_by",
            "make_ref",
            "model_ref",
        )
        qs = CarQueryService._prefetch_all_images(qs)
        qs = qs.prefetch_related(
            Prefetch("bids", queryset=top_bids_qs, to_attr="top_bids")
        )
        qs = qs.annotate(
            bid_count=Count("bids", distinct=True),
            highest_bid=Max("bids__amount"),
            dealer_avg=Coalesce(
                Avg("dealer__ratings__rating"),
                0.0,
                output_field=FloatField()
            )
        )
        return qs

    @staticmethod
    def get_visible_cars_for_user(user, queryset):
        """
        Apply role-based visibility for any user.
        Dealers, brokers, sellers, admins, and buyers handled.
        """
        if not user.is_authenticated:
            qs = queryset.filter(verification_status="verified")

        elif has_role(user, ["super_admin", "admin"]):
            qs = queryset

        elif has_role(user, "dealer"):
            qs = queryset.filter(
                Q(dealer__profile__user=user) |
                Q(verification_status="verified")
            )

        elif has_role(user, "seller"):
            qs = queryset.filter(dealer__dealerstaff__user=user)

        elif has_role(user, "broker"):
            qs = queryset.filter(
                Q(broker__profile__user=user) |
                Q(verification_status="verified")
            )

        else:
            qs = queryset.filter(verification_status="verified")

        # Ensure featured images are always prefetched for list/detail
        if hasattr(queryset, "model") and queryset.model == Car:
            qs = CarQueryService._prefetch_featured_image(qs)

        return qs

    @staticmethod
    def get_verification_cars_for_user(user, verification_status=None):
        """
        Returns cars for verification screens depending on user role.
        """
        qs = CarQueryService.base_queryset()

        if has_role(user, ["super_admin", "admin"]):
            pass
        elif has_role(user, "dealer"):
            qs = qs.filter(dealer__profile_id=getattr(user, "dealer_profile_id", None))
        elif has_role(user, "broker"):
            qs = qs.filter(broker__profile_id=getattr(user, "broker_profile_id", None))
        else:
            raise PermissionDenied("You are not allowed to view verification records.")

        if verification_status:
            qs = qs.filter(verification_status=verification_status)

        # Prefetch featured images for verification lists too
        qs = CarQueryService._prefetch_featured_image(qs)
        return qs.order_by("-created_at")
