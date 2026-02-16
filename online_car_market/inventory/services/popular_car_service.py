from django.db.models import F
from online_car_market.inventory.models import Car
from decimal import Decimal, InvalidOperation

class PopularCarService:

    @staticmethod
    def base_queryset():
        """
        Base queryset for popular cars.
        Only verified cars are publicly visible.
        """
        return Car.objects.filter(verification_status="verified")

    @staticmethod
    def apply_price_filters(queryset, min_price=None, max_price=None):
        try:
            if min_price:
                queryset = queryset.filter(price__gte=Decimal(min_price))
            if max_price:
                queryset = queryset.filter(price__lte=Decimal(max_price))
        except (InvalidOperation, TypeError):
            pass

        return queryset

    @staticmethod
    def get_popular_cars(min_price=None, max_price=None):
        """
        Return filtered and ordered popular cars.
        """
        qs = PopularCarService.base_queryset()
        qs = PopularCarService.apply_price_filters(qs, min_price, max_price)
        return qs.order_by("-views")

    @staticmethod
    def increment_views(car):
        """
        Safely increment car view count.
        """
        car.views = F("views") + 1
        car.save(update_fields=["views"])
        car.refresh_from_db()
        return car

