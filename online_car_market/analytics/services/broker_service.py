from django.db.models import Avg, Count, Sum, Q
from online_car_market.brokers.models import BrokerProfile
from online_car_market.payment.models import Payment

class BrokerAnalyticsService:

    @staticmethod
    def get_broker_analytics(broker: BrokerProfile):
        """
        Expects a BrokerProfile instance.
        """
        total_cars = broker.cars.count()
        sold_cars = broker.cars.filter(status="sold").count()

        average_price = (
            broker.cars.filter(price__isnull=False)
            .aggregate(avg=Avg("price"))["avg"] or 0
        )

        total_money_made = (
            broker.cars.filter(status="sold")
            .aggregate(sum=Sum("price"))["sum"] or 0
        )
        payment_stats = Payment.objects.filter(broker=broker).aggregate(
            total_payments=Count("id"),
            completed_payments=Count("id", filter=Q(status="completed")),
            total_amount_paid=Sum("amount", filter=Q(status="completed")),
        )

        return {
            "total_cars": total_cars,
            "sold_cars": sold_cars,
            "average_price": round(average_price, 2),
            "total_money_made": round(total_money_made, 2),
            "payment_stats": {
                "total_payments": payment_stats["total_payments"],
                "completed_payments": payment_stats["completed_payments"],
                "total_amount_paid": round(payment_stats["total_amount_paid"] or 0, 2),
            },
        }
