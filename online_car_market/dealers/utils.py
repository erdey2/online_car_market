# online_car_market/dealers/utils.py

from django.db.models import Count
from django.utils import timezone
from datetime import datetime, timedelta
from online_car_market.dealers.models import DealerStaff
from online_car_market.users.models import User
from online_car_market.inventory.models import Car
from online_car_market.sales.models import Sale
from rolepermissions.checkers import get_user_roles

def get_top_sellers(month=None, limit=5):
    """Get top sellers by number of cars sold in the specified month."""
    today = timezone.now()
    if month is None:
        month = today.month
        year = today.year
    else:
        year = month.year
        month = month.month

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    # Aggregate sales per seller (using posted_by from Car)
    sales_data = Sale.objects.filter(
        date__gte=start_date,
        date__lt=end_date
    ).values('car__posted_by').annotate(total_sales=Count('id')).order_by('-total_sales')

    # Filter for users with 'seller' role and limit results
    top_sellers = []
    for sale in sales_data:
        user_id = sale['car__posted_by']
        user = User.objects.get(id=user_id)
        if 'seller' in [r.__name__.lower() for r in get_user_roles(user)]:
            top_sellers.append({
                'user_email': user.email,
                'total_sales': sale['total_sales'],
                'month': month,
                'year': year
            })

    return sorted(top_sellers, key=lambda x: x['total_sales'], reverse=True)[:limit]

def get_high_sales_rate_cars(month=None, limit=5):
    """Get cars with the highest sales rate (number of sales) in the specified month."""
    today = timezone.now()
    if month is None:
        month = today.month
        year = today.year
    else:
        year = month.year
        month = month.month

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    # Aggregate sales per car
    car_sales = Sale.objects.filter(
        date__gte=start_date,
        date__lt=end_date
    ).values('car').annotate(sale_count=Count('id')).order_by('-sale_count')

    # Fetch car details and limit results
    top_cars = []
    for car_data in car_sales[:limit]:
        car_id = car_data['car']
        car = Car.objects.get(id=car_id)
        top_cars.append({
            'car_details': f"{car.make} {car.model} ({car.year})",
            'sale_count': car_data['sale_count'],
            'month': month,
            'year': year
        })

    return top_cars
