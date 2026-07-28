from decimal import Decimal, InvalidOperation
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import Car

class CarFilterService:

    @staticmethod
    def _validate_choice(value, choices, field_name):
        valid_choices = [choice[0] for choice in choices]

        if value and value not in valid_choices:
            raise ValidationError(
                f"Invalid {field_name}. Must be one of: "
                f"{', '.join(valid_choices)}."
            )

    @staticmethod
    def _parse_int(value, field_name):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValidationError(
                f"{field_name} must be a valid integer."
            )

    @staticmethod
    def _parse_price(value, field_name):
        try:
            value = Decimal(value)
        except (TypeError, InvalidOperation):
            raise ValidationError(
                f"{field_name} must be a valid number."
            )

        if value < 0:
            raise ValidationError(
                f"{field_name} cannot be negative."
            )

        return value

    @staticmethod
    def filter_cars(queryset, query_params):
        fuel_type = query_params.get("fuel_type")
        sale_type = query_params.get("sale_type")

        make_ref = query_params.get("make_ref")
        model_ref = query_params.get("model_ref")

        make = query_params.get("make")
        model = query_params.get("model")

        price_min = query_params.get("price_min")
        price_max = query_params.get("price_max")

        # Fuel type
        if fuel_type:
            CarFilterService._validate_choice(
                fuel_type,
                Car.FUEL_TYPES,
                "fuel type",
            )
            queryset = queryset.filter(
                fuel_type=fuel_type
            )

        # Sale type
        if sale_type:
            CarFilterService._validate_choice(
                sale_type,
                Car.SALE_TYPES,
                "sale type",
            )
            queryset = queryset.filter(
                sale_type=sale_type
            )

        # Make ID
        if make_ref:
            queryset = queryset.filter(
                make_ref_id=CarFilterService._parse_int(
                    make_ref,
                    "Make ID",
                )
            )

        # Model ID
        if model_ref:
            queryset = queryset.filter(
                model_ref_id=CarFilterService._parse_int(
                    model_ref,
                    "Model ID",
                )
            )

        # Make name
        if make:
            queryset = queryset.filter(
                Q(make__iexact=make) |
                Q(make_ref__name__iexact=make)
            )

        # Model name
        if model:
            queryset = queryset.filter(
                Q(model__iexact=model) |
                Q(model_ref__name__iexact=model)
            )

        # Price
        min_price = None

        if price_min:
            min_price = CarFilterService._parse_price(
                price_min,
                "Minimum price",
            )
            queryset = queryset.filter(
                price__gte=min_price
            )

        if price_max:
            max_price = CarFilterService._parse_price(
                price_max,
                "Maximum price",
            )

            if min_price is not None and max_price < min_price:
                raise ValidationError(
                    "Maximum price cannot be less than minimum price."
                )

            queryset = queryset.filter(
                price__lte=max_price
            )

        return queryset
