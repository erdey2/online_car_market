from django.db.models import Avg, Count, Subquery, OuterRef
from online_car_market.inventory.models import Car, CarImage


class BuyerAnalyticsService:

    @staticmethod
    def get_buyer_analytics():
        cheapest_subquery = (
            Car.objects.filter(
                verification_status="verified",
                make_ref=OuterRef("make_ref"),
                model_ref=OuterRef("model_ref"),
            )
            .exclude(status="sold")
            .order_by("price")
        )

        analytics = (
            Car.objects.filter(verification_status="verified")
            .exclude(status="sold")
            .values("make_ref__name", "model_ref__name")
            .annotate(
                average_price=Avg("price"),
                total_cars=Count("id"),
                cheapest_car_id=Subquery(cheapest_subquery.values("id")[:1]),
                cheapest_car_price=Subquery(cheapest_subquery.values("price")[:1]),
            )
            .order_by("make_ref__name")
        )

        cheapest_ids = [a["cheapest_car_id"] for a in analytics if a["cheapest_car_id"]]

        images = CarImage.objects.filter(
            car_id__in=cheapest_ids,
            is_featured=True,
        ).values("car_id", "image")

        image_map = {i["car_id"]: str(i["image"].url) for i in images}

        formatted = []

        for item in analytics:
            cheapest_id = item["cheapest_car_id"]

            formatted.append({
                "car_make": item["make_ref__name"],
                "car_model": item["model_ref__name"],
                "average_price": item["average_price"],
                "total_cars": item["total_cars"],
                "cheapest_car": {
                    "id": cheapest_id,
                    "price": item["cheapest_car_price"],
                    "image_url": image_map.get(cheapest_id),
                } if cheapest_id else None,
            })

        return {"car_summary": formatted}
