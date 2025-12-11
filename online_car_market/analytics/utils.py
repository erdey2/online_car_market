from datetime import datetime
from django.db.models import Count, Q
from online_car_market.dealers.models import DealerProfile
from online_car_market.inventory.models import Car
from django.utils import timezone


def parse_month_year(month, year):
    if not month:
        return None
    try:
        return datetime(int(year or timezone.now().year), int(month), 1)
    except ValueError:
        return None


def get_top_sellers(month_date=None):
    queryset = DealerProfile.objects.annotate(
        total_sales=Count('cars', filter=Q(cars__status='sold'))
    ).order_by('-total_sales')

    data = []
    for dealer in queryset:
        data.append({
            "user_email": dealer.profile.user.email,
            "total_sales": dealer.total_sales,
            "month": month_date.month if month_date else None,
            "year": month_date.year if month_date else None,
        })
    return data


def get_high_sales_rate_cars(month_date=None):
    queryset = Car.objects.filter(status='sold').annotate(
        sale_count=Count('id')
    ).order_by('-sale_count')

    data = []
    for car in queryset:
        data.append({
            "car_details": f"{car.make_ref.name} {car.model_ref.name}",
            "sale_count": 1,
            "month": month_date.month if month_date else None,
            "year": month_date.year if month_date else None,
        })
    return data
