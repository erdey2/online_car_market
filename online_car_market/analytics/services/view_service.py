from django.db.models import Count, F, Q
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Value, CharField, Case, When
from django.db.models.functions import Coalesce
from online_car_market.inventory.models import CarView


class CarViewAnalyticsService:

    TRUNC_MAP = {
        "day": TruncDay,
        "week": TruncWeek,
        "month": TruncMonth,
        "year": TruncYear,
    }

    # Aggregated View Analytics (period grouping)
    @classmethod
    def get_view_analytics(cls, filters: dict):

        range_type = filters.get("range", "month")
        car_id = filters.get("car_id")
        dealer_id = filters.get("dealer_id")
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")

        trunc_func = cls.TRUNC_MAP.get(range_type, TruncMonth)("viewed_at")

        queryset = CarView.objects.select_related(
            "car",
            "car__dealer",
            "car__make_ref",
            "car__model_ref",
        )

        if car_id:
            queryset = queryset.filter(car_id=car_id)

        if dealer_id:
            queryset = queryset.filter(car__dealer_id=dealer_id)

        if date_from:
            queryset = queryset.filter(viewed_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(viewed_at__date__lte=date_to)

        analytics = (
            queryset
            .annotate(
                period=trunc_func,
                make=F("car__make_ref__name"),
                model=F("car__model_ref__name"),
                dealer_id=F("car__dealer_id"),
            )
            .values(
                "car_id",
                "dealer_id",
                "make",
                "model",
                "period",
            )
            .annotate(
                total_views=Count("id"),
                unique_viewers=Count("user", distinct=True),
            )
            .order_by("-period", "-total_views")
        )

        return list(analytics)

    # View Viewers (Detailed)
    @staticmethod
    def get_view_viewers(filters: dict):

        queryset = CarView.objects.select_related(
            "user",
            "user__profile",
            "car",
            "car__dealer",
        )

        if filters.get("car_id"):
            queryset = queryset.filter(car_id=filters["car_id"])

        if filters.get("dealer_id"):
            queryset = queryset.filter(car__dealer_id=filters["dealer_id"])

        if filters.get("date_from"):
            queryset = queryset.filter(viewed_at__date__gte=filters["date_from"])

        if filters.get("date_to"):
            queryset = queryset.filter(viewed_at__date__lte=filters["date_to"])

        data = (
            queryset
            .annotate(
                first_name=Coalesce("user__profile__first_name", Value("")),
                last_name=Coalesce("user__profile__last_name", Value("")),
                contact=Coalesce("user__profile__contact", Value("")),
                viewer_type=Case(
                    When(user__isnull=True, then=Value("anonymous")),
                    default=Value("registered"),
                    output_field=CharField(),
                ),
            )
            .values(
                "car_id",
                "user_id",
                "user__email",
                "first_name",
                "last_name",
                "contact",
                "viewed_at",
                "viewer_type",
            )
            .order_by("-viewed_at")
        )

        return list(data)

    # Dealer View Analytics
    @staticmethod
    def get_dealer_view_analytics(dealer):

        analytics = (
            CarView.objects.filter(car__dealer=dealer)
            .annotate(
                car_pk=F("car__id"),
                car_make=F("car__make_ref__name"),
                car_model=F("car__model_ref__name"),
            )
            .values(
                "car_pk",
                "car_make",
                "car_model",
            )
            .annotate(
                total_unique_views=Count("user", distinct=True),
                viewer_emails=ArrayAgg("user__email", distinct=True),
            )
            .order_by("-total_unique_views")
        )

        return list(analytics)

    # Broker View Analytics
    @staticmethod
    def get_broker_view_analytics(broker):
        analytics = (
            CarView.objects.filter(car__broker=broker)
            .annotate(
                car_pk=F("car__id"),
                car_make=F("car__make_ref__name"),
                car_model=F("car__model_ref__name"),
            )
            .values(
                "car_pk",
                "car_make",
                "car_model",
            )
            .annotate(
                total_unique_views=Count("user", distinct=True),
                viewer_emails=ArrayAgg("user__email", distinct=True),
            )
            .order_by("-total_unique_views")
        )

        return list(analytics)
