from datetime import datetime
from django.db.models import Count, Q, F, Window
from django.db.models.functions import DenseRank
from django.utils import timezone
from online_car_market.dealers.models import DealerProfile
from online_car_market.inventory.models import Car


def parse_month_year(month, year):
    if not month:
        return None
    try:
        return datetime(int(year or timezone.now().year), int(month), 1)
    except (ValueError, TypeError):
        return None


def get_top_sellers(month_date=None):
    """
    Top dealers by number of cars sold in the given month (using accurate sold_at).
    """
    queryset = DealerProfile.objects.all()

    # Base filter: sold cars with sold_at set
    sold_filter = Q(cars__status='sold') & Q(cars__sold_at__isnull=False)

    if month_date:
        sold_filter &= Q(
            cars__sold_at__year=month_date.year,
            cars__sold_at__month=month_date.month
        )

    queryset = queryset.annotate(
        total_sales=Count('cars', filter=sold_filter)
    ).filter(total_sales__gt=0)

    queryset = queryset.annotate(rank=Window(expression=DenseRank(), order_by=F('total_sales').desc())).order_by('rank')[:20]

    data = []
    for dealer in queryset:
        data.append({
            "dealer_id": dealer.id,
            "dealer_name": dealer.company_name or "Unnamed Dealer",
            "user_email": dealer.profile.user.email,
            "total_sales": dealer.total_sales,
            "rank": dealer.rank,
            "month": month_date.month if month_date else None,
            "year": month_date.year if month_date else None,
        })
    return data


def get_high_sales_rate_cars(month_date=None):
    """
    Top make/model by sales volume in the month (using sold_at).
    """
    queryset = Car.objects.filter(
        status='sold',
        sold_at__isnull=False
    )

    if month_date:
        queryset = queryset.filter(
            sold_at__year=month_date.year,
            sold_at__month=month_date.month
        )

    stats = (
        queryset
        .values('make_ref__name', 'model_ref__name')
        .annotate(sale_count=Count('id'))
        .filter(sale_count__gt=0)
        .order_by('-sale_count')
    )

    stats = stats.annotate(rank=Window(expression=DenseRank(), order_by=F('sale_count').desc()))[:20]

    data = []
    for stat in stats:
        data.append({
            "make": stat['make_ref__name'],
            "model": stat['model_ref__name'],
            "sale_count": stat['sale_count'],
            "rank": stat['rank'],
            "month": month_date.month if month_date else None,
            "year": month_date.year if month_date else None,
        })
    return data
