from django.db.models import Avg, Count, Q, F
from online_car_market.inventory.models import Car, CarMake
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile


class PlatformAnalyticsService:

    @staticmethod
    def get_platform_analytics():
        total_cars = Car.objects.count()

        average_price = (
            Car.objects.filter(price__isnull=False)
            .aggregate(avg=Avg("price"))["avg"] or 0
        )

        dealer_stats = DealerProfile.objects.annotate(
            total_cars=Count("cars"),
            sold_cars=Count("cars", filter=Q(cars__status="sold")),
            avg_price=Avg("cars__price"),
            dealer_name=F("company_name"),
        ).values("id", "dealer_name", "total_cars", "sold_cars", "avg_price")

        broker_stats = BrokerProfile.objects.annotate(
            total_cars=Count("cars"),
            sold_cars=Count("cars", filter=Q(cars__status="sold")),
            avg_price=Avg("cars__price"),
            broker_name=F("profile__user__email"),
        ).values("id", "broker_name", "total_cars", "sold_cars", "avg_price")

        make_stats = CarMake.objects.annotate(
            total_cars=Count("cars"),
            avg_price=Avg("cars__price"),
        ).values("name", "total_cars", "avg_price")

        return {
            "total_cars": total_cars,
            "average_price": round(average_price, 2),
            "dealer_stats": list(dealer_stats),
            "broker_stats": list(broker_stats),
            "make_stats": list(make_stats),
        }
