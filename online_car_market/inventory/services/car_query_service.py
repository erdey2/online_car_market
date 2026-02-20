from django.db.models import Avg, Max, Count, FloatField, Prefetch, Q
from django.db.models.functions import Coalesce
from rest_framework.exceptions import PermissionDenied
from online_car_market.inventory.models import Car, CarImage
from online_car_market.bids.models import Bid
from rolepermissions.checkers import has_role

class CarQueryService:

    @staticmethod
    def base_queryset():
        return Car.objects.all()

    @staticmethod
    def _prefetch_featured_image(queryset):
        """Prefetch only the featured image for list view."""
        featured_qs = CarImage.objects.filter(is_featured=True).only("id", "image", "is_featured")
        return queryset.prefetch_related(Prefetch("images", queryset=featured_qs, to_attr="featured_images"))

    @staticmethod
    def for_list():
        """List view: only one featured image."""
        featured_qs = CarImage.objects.filter(is_featured=True).only("id", "image", "is_featured")
        prefetch_images = Prefetch("images", queryset=featured_qs, to_attr="featured_images")

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
        """Detail view: prefetch all images and top 10 bids."""
        all_images_qs = CarImage.objects.all().only("id", "image", "is_featured")
        top_bids_qs = Bid.objects.select_related("user").only(
            "id", "amount", "user_id", "created_at"
        ).order_by("-amount")[:10]

        return (
            Car.objects
            .select_related(
                "dealer", "dealer__profile", "broker", "broker__profile",
                "posted_by", "make_ref", "model_ref"
            )
            .prefetch_related(
                Prefetch("images", queryset=all_images_qs),  # normal prefetch
                Prefetch("bids", queryset=top_bids_qs, to_attr="top_bids")
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
        """
        Role-based filtering. Do NOT touch prefetching here to avoid conflicts.
        Only filter the queryset; prefetch is handled in for_list / for_detail.
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

        return qs

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
            raise PermissionDenied("You are not allowed to view verification records.")

        if verification_status:
            qs = qs.filter(verification_status=verification_status)

        return CarQueryService._prefetch_featured_image(qs).order_by("-created_at")
