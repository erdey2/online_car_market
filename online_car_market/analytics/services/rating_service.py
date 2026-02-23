from django.db.models import Avg, Count, Q, F, Value, CharField
from django.db.models.functions import Coalesce
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models.functions import JSONObject

from online_car_market.rating.models import CarRating


class RatingAnalyticsService:

    @staticmethod
    def get_rating_analytics(filters: dict):
        """
        filters = {
            "car_id": int | None,
            "dealer_id": int | None,
            "date_from": str | None,
            "date_to": str | None,
        }
        """

        queryset = CarRating.objects.select_related(
            "car",
            "car__dealer",
            "car__make_ref",
            "car__model_ref",
            "user",
        )

        # ---- Apply Filters ----
        if filters.get("car_id"):
            queryset = queryset.filter(car_id=filters["car_id"])

        if filters.get("dealer_id"):
            queryset = queryset.filter(car__dealer_id=filters["dealer_id"])

        if filters.get("date_from"):
            queryset = queryset.filter(created_at__date__gte=filters["date_from"])

        if filters.get("date_to"):
            queryset = queryset.filter(created_at__date__lte=filters["date_to"])

        analytics = (
            queryset
            .values(
                "car_id",
                "car__dealer_id",
                "car__make_ref__name",
                "car__model_ref__name",
            )
            .annotate(
                average_rating=Avg("rating"),
                total_ratings=Count("id"),

                rating_1=Count("id", filter=Q(rating=1)),
                rating_2=Count("id", filter=Q(rating=2)),
                rating_3=Count("id", filter=Q(rating=3)),
                rating_4=Count("id", filter=Q(rating=4)),
                rating_5=Count("id", filter=Q(rating=5)),

                reviews=ArrayAgg(
                    JSONObject(
                        email=Coalesce(F("user__email"), Value("")),
                        rating=F("rating"),
                        comment=F("comment"),
                        created_at=F("created_at"),
                    ),
                    filter=Q(comment__isnull=False),
                    distinct=True,
                ),
            )
            .order_by("-average_rating", "-total_ratings")
        )

        return list(analytics)
