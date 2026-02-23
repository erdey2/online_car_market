from django.db.models import Avg, Count, Sum
from online_car_market.dealers.models import DealerProfile
from online_car_market.inventory.models import Car

class DealerAnalyticsService:

    @staticmethod
    def get_dealer_analytics(dealer: DealerProfile):
        """
        Returns dealer-level analytics:
        - total cars
        - sold cars
        - average price
        - model-wise stats
        """
        # Total cars for dealer
        total_cars = dealer.cars.count()

        # Sold cars
        sold_cars = dealer.cars.filter(status='sold').count()

        # Average price of sold cars
        average_price = dealer.cars.filter(price__isnull=False).aggregate(Avg('price'))['price__avg'] or 0

        # Model-wise statistics
        model_stats_qs = dealer.cars.filter(status='sold', price__isnull=False).values(
            'make_ref__name', 'model_ref__name'
        ).annotate(
            total_sold=Count('id'),
            total_sales=Sum('price'),
            avg_price=Avg('price')
        ).order_by('-total_sold')

        # Convert queryset to list of dicts
        model_stats = [
            {
                "make_name": stat['make_ref__name'],
                "model_name": stat['model_ref__name'],
                "total_sold": stat['total_sold'],
                "total_sales": round(stat['total_sales'], 2),
                "avg_price": round(stat['avg_price'], 2)
            } for stat in model_stats_qs
        ]

        return {
            "total_cars": total_cars,
            "sold_cars": sold_cars,
            "average_price": round(average_price, 2),
            "model_stats": model_stats
        }
