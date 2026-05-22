from django.db.models import Max, Value, IntegerField, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal, InvalidOperation
from online_car_market.inventory.models import Car


class PopularCarService:

    @staticmethod
    def base_queryset():
        return (
            Car.objects
            .filter(
                verification_status="verified"
            )
            .select_related(
                "make_ref",
                "model_ref",
                "dealer",
                "broker",
                "posted_by",
                "dealer__profile__user",
                "broker__profile__user",
                "posted_by__profile__user",
            )
            .prefetch_related(
                "images"
            )
            .annotate(
                highest_bid=Coalesce(
                    Max("bids__amount"),
                    Value(0),
                    output_field=DecimalField(
                        max_digits=10,
                        decimal_places=2,
                    ),
                ),
                views_count_coalesced=Coalesce(
                    "views_count",
                    Value(0),
                    output_field=IntegerField(),
                ),
            )
        )

    @staticmethod
    def apply_price_filters(queryset, min_price=None, max_price=None):
        try:
            if min_price:
                queryset = queryset.filter(
                    price__gte=Decimal(min_price)
                )

            if max_price:
                queryset = queryset.filter(
                    price__lte=Decimal(max_price)
                )

        except (InvalidOperation, TypeError):
            pass

        return queryset

    @staticmethod
    def get_popular_cars(min_price=None, max_price=None):
        qs = PopularCarService.base_queryset()
        qs = PopularCarService.apply_price_filters(
            qs,
            min_price,
            max_price
        )
        return qs
