from django.db.models import Q
from rest_framework.exceptions import ValidationError
from ..models import Car, CarMake, CarModel

class CarFilterService:

    @staticmethod
    def filter_cars(queryset, query_params):
        fuel_type = query_params.get("fuel_type")
        price_min = query_params.get("price_min")
        price_max = query_params.get("price_max")
        sale_type = query_params.get("sale_type")
        make_ref = query_params.get("make_ref")
        model_ref = query_params.get("model_ref")
        make = query_params.get("make")
        model = query_params.get("model")

        # Validate fuel type
        valid_fuel_types = [choice[0] for choice in Car.FUEL_TYPES]
        if fuel_type:
            if fuel_type not in valid_fuel_types:
                raise ValidationError(
                    f"Invalid fuel type. Must be one of: {', '.join(valid_fuel_types)}."
                )
            queryset = queryset.filter(fuel_type=fuel_type)

        # Validate sale type
        valid_sale_types = [choice[0] for choice in Car.SALE_TYPES]
        if sale_type:
            if sale_type not in valid_sale_types:
                raise ValidationError(
                    f"Invalid sale type. Must be one of: {', '.join(valid_sale_types)}."
                )
            queryset = queryset.filter(sale_type=sale_type)

        # Validate make_ref
        if make_ref:
            try:
                make_ref = int(make_ref)
            except ValueError:
                raise ValidationError("Make ID must be a valid integer.")

            if not CarMake.objects.filter(id=make_ref).exists():
                raise ValidationError("Invalid make ID.")

            queryset = queryset.filter(make_ref=make_ref)

        # Validate model_ref
        if model_ref:
            try:
                model_ref = int(model_ref)
            except ValueError:
                raise ValidationError("Model ID must be a valid integer.")

            if not CarModel.objects.filter(id=model_ref).exists():
                raise ValidationError("Invalid model ID.")

            queryset = queryset.filter(model_ref=model_ref)

        # Validate make name
        if make:
            if not CarMake.objects.filter(name__iexact=make).exists():
                raise ValidationError("Invalid make name.")

            queryset = queryset.filter(
                Q(make=make) | Q(make_ref__name__iexact=make)
            )

        # Validate model name
        if model:
            if not CarModel.objects.filter(name__iexact=model).exists():
                raise ValidationError("Invalid model name.")

            queryset = queryset.filter(
                Q(model=model) | Q(model_ref__name__iexact=model)
            )

        # Price validation
        try:
            if price_min:
                price_min = float(price_min)
                if price_min < 0:
                    raise ValidationError("Minimum price cannot be negative.")
                queryset = queryset.filter(price__gte=price_min)

            if price_max:
                price_max = float(price_max)
                if price_max < 0:
                    raise ValidationError("Maximum price cannot be negative.")
                if price_min and price_max < price_min:
                    raise ValidationError(
                        "Maximum price cannot be less than minimum price."
                    )
                queryset = queryset.filter(price__lte=price_max)

        except ValueError:
            raise ValidationError("Price parameters must be valid numbers.")

        return queryset
