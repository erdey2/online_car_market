import logging
from django.db.models import Avg, Count, Sum, Q, F, Subquery, OuterRef, Value, CharField, Case, When
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear, Coalesce
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models.functions import JSONObject
from rest_framework.permissions import AllowAny

from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
from rest_framework import status

from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from online_car_market.inventory.models import Car, CarMake, CarView, CarImage
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.payment.models import Payment
from online_car_market.accounting.models import Expense, CarExpense, Revenue
from online_car_market.rating.models import CarRating
from online_car_market.users.permissions.drf_permissions import (IsSuperAdminOrAdminOrDealer, IsSuperAdminOrAdminOrBroker,
                                                                 IsSuperAdminOrAdmin, IsDealer, IsBuyer, IsBroker)
from ..utils import get_top_sellers, get_high_sales_rate_cars, parse_month_year

logger = logging.getLogger(__name__)


class AnalyticsViewSet(ViewSet):
    """ Analytics endpoints """

    @extend_schema(
        tags=["Analytics"],
        description="Get market analytics (super admin or admin only).",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "total_cars": {"type": "integer"},
                    "average_price": {"type": "number"},
                    "dealer_stats": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "dealer_id": {"type": "integer"},
                                "dealer_name": {"type": "string"},
                                "total_cars": {"type": "integer"},
                                "sold_cars": {"type": "integer"},
                                "average_price": {"type": "number"}
                            }
                        }
                    },
                    "broker_stats": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "broker_id": {"type": "integer"},
                                "broker_name": {"type": "string"},
                                "total_cars": {"type": "integer"},
                                "sold_cars": {"type": "integer"},
                                "average_price": {"type": "number"}
                            }
                        }
                    },
                    "make_stats": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "make_name": {"type": "string"},
                                "total_cars": {"type": "integer"},
                                "average_price": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path="platform-analytics", permission_classes=[IsSuperAdminOrAdmin])
    def analytics(self, request):
        # Restrict to super admin or admin
        if not has_role(request.user, ['super_admin', 'admin']):
            return Response(
                {"error": "Only super admin or admin can access this analytics."}, status=status.HTTP_403_FORBIDDEN)

        total_cars = Car.objects.count()
        average_price = Car.objects.filter(price__isnull=False).aggregate(Avg('price'))['price__avg'] or 0

        dealer_stats = DealerProfile.objects.annotate(
            total_cars=Count('cars'),
            sold_cars=Count('cars', filter=Q(cars__status='sold')),
            avg_price=Avg('cars__price'),
            dealer_name=F('company_name')
        ).values('id', 'dealer_name', 'total_cars', 'sold_cars', 'avg_price')

        broker_stats = BrokerProfile.objects.annotate(
            total_cars=Count('cars'),
            sold_cars=Count('cars', filter=Q(cars__status='sold')),
            avg_price=Avg('cars__price'),
            broker_name=F('profile__user__email')
        ).values('id', 'broker_name', 'total_cars', 'sold_cars', 'avg_price')

        make_stats = CarMake.objects.annotate(
            total_cars=Count('cars'),
            avg_price=Avg('cars__price')
        ).values('name', 'total_cars', 'avg_price')

        return Response({
            "total_cars": total_cars,
            "average_price": round(average_price, 2),
            "dealer_stats": list(dealer_stats),
            "broker_stats": list(broker_stats),
            "make_stats": list(make_stats)
        })

    @extend_schema(
        tags=["Analytics"],
        description="Buyer analytics: average price, total cars, and cheapest verified car per make/model.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "car_summary": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "car_make": {"type": "string"},
                                "car_model": {"type": "string"},
                                "average_price": {"type": "number"},
                                "total_cars": {"type": "integer"},
                                "cheapest_car": {
                                    "type": ["object", "null"],
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "price": {"type": "number"},
                                        "image_url": {"type": ["string", "null"]}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            500: OpenApiResponse(description="Internal server error"),
        }
    )
    @action(detail=False, methods=['get'], url_path='buyer-analytics', permission_classes = [AllowAny])
    def buyer_analytics(self, request):
        try:
            # Subquery for cheapest car per make/model
            cheapest_car_subquery = Car.objects.filter(
                verification_status='verified',
                make_ref=OuterRef('make_ref'),
                model_ref=OuterRef('model_ref')
            ).exclude(status='sold').order_by('price').values('id', 'price')[:1]

            # Main analytics
            analytics = (
                Car.objects.filter(verification_status='verified')
                .exclude(status='sold')
                .values('make_ref__name', 'model_ref__name')
                .annotate(
                    average_price=Avg('price'),
                    total_cars=Count('id'),
                    cheapest_car_id=Subquery(cheapest_car_subquery.values('id')[:1]),
                    cheapest_car_price=Subquery(cheapest_car_subquery.values('price')[:1]),
                )
                .order_by('make_ref__name', 'model_ref__name')
            )

            # Fetch featured images for all cheapest cars
            cheapest_car_ids = [item['cheapest_car_id'] for item in analytics if item['cheapest_car_id']]
            featured_images = CarImage.objects.filter(car_id__in=cheapest_car_ids, is_featured=True).values('car_id', 'image')

            # Convert CloudinaryResource to URL
            featured_image_map = {img['car_id']: str(img['image'].url) for img in featured_images}

            # Format response
            formatted = []
            for item in analytics:
                cheapest_id = item['cheapest_car_id']
                formatted.append({
                    "car_make": item['make_ref__name'],
                    "car_model": item['model_ref__name'],
                    "average_price": item['average_price'],
                    "total_cars": item['total_cars'],
                    "cheapest_car": {
                        "id": cheapest_id,
                        "price": item['cheapest_car_price'],
                        "image_url": featured_image_map.get(cheapest_id)
                    } if cheapest_id else None
                })

            return Response({"car_summary": formatted})

        except Exception as e:
            logger.exception(f"Error in buyer_analytics for user {request.user.id}: {str(e)}")
            return Response({"error": "Internal server error"}, status=500)

    @extend_schema(
        tags=["Analytics"],
        description="Get analytics for brokers, including total money made and payment stats.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "total_cars": {"type": "integer"},
                    "sold_cars": {"type": "integer"},
                    "average_price": {"type": "number"},
                    "total_money_made": {"type": "number"},
                    "payment_stats": {
                        "type": "object",
                        "properties": {
                            "total_payments": {"type": "integer"},
                            "completed_payments": {"type": "integer"},
                            "total_amount_paid": {"type": "number"}
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='broker-analytics', permission_classes=[IsBroker])
    def broker_analytics(self, request):
        if not has_role(request.user, ['broker']):
            return Response({"error": "Only brokers can access this analytics."}, status=status.HTTP_403_FORBIDDEN)
        try:
            broker = BrokerProfile.objects.get(profile__user=request.user)
        except BrokerProfile.DoesNotExist:
            return Response({"error": "Broker profile not found."}, status=status.HTTP_404_NOT_FOUND)
        total_cars = broker.cars.count()
        sold_cars = broker.cars.filter(status='sold').count()
        average_price = broker.cars.filter(price__isnull=False).aggregate(Avg('price'))['price__avg'] or 0
        total_money_made = broker.cars.filter(status='sold', price__isnull=False).aggregate(Sum('price'))[
                               'price__sum'] or 0
        payment_stats = Payment.objects.filter(broker=broker).aggregate(
            total_payments=Count('id'),
            completed_payments=Count('id', filter=Q(status='completed')),
            total_amount_paid=Sum('amount', filter=Q(status='completed'))
        )
        return Response({
            "total_cars": total_cars,
            "sold_cars": sold_cars,
            "average_price": round(average_price, 2),
            "total_money_made": round(total_money_made, 2),
            "payment_stats": {
                "total_payments": payment_stats['total_payments'],
                "completed_payments": payment_stats['completed_payments'],
                "total_amount_paid": round(payment_stats['total_amount_paid'] or 0, 2)
            }
        })

    @extend_schema(
        tags=["Analytics"],
        description="Get analytics for dealers, including detailed sales by car make/model.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "total_cars": {"type": "integer"},
                    "sold_cars": {"type": "integer"},
                    "average_price": {"type": "number"},
                    "model_stats": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "make_name": {"type": "string"},
                                "model_name": {"type": "string"},
                                "total_sold": {"type": "integer"},
                                "total_sales": {"type": "number"},
                                "avg_price": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='dealer-analytics', permission_classes=[IsDealer])
    def dealer_analytics(self, request):
        if not has_role(request.user, ['dealer']):
            return Response({"error": "Only dealers can access this analytics."}, status=status.HTTP_403_FORBIDDEN)
        try:
            dealer = DealerProfile.objects.get(profile__user=request.user)
        except DealerProfile.DoesNotExist:
            return Response({"error": "Dealer profile not found."}, status=status.HTTP_404_NOT_FOUND)
        total_cars = dealer.cars.count()
        sold_cars = dealer.cars.filter(status='sold').count()
        average_price = dealer.cars.filter(price__isnull=False).aggregate(Avg('price'))['price__avg'] or 0
        model_stats = dealer.cars.filter(status='sold', price__isnull=False).values(
            'make_ref__name', 'model_ref__name'
        ).annotate(total_sold=Count('id'), total_sales=Sum('price'), avg_price=Avg('price')).order_by('-total_sold')
        return Response({
            "total_cars": total_cars,
            "sold_cars": sold_cars,
            "average_price": round(average_price, 2),
            "model_stats": [
                {
                    "make_name": stat['make_ref__name'],
                    "model_name": stat['model_ref__name'],
                    "total_sold": stat['total_sold'],
                    "total_sales": round(stat['total_sales'], 2),
                    "avg_price": round(stat['avg_price'], 2)
                } for stat in model_stats
            ]
        })

    @extend_schema(
        tags=["Analytics"],
        description="Retrieve the top sellers based on the number of cars sold in the specified month.",
        parameters=[
            OpenApiParameter(name="month", type=int, location="query", description="Month (1-12)"),
            OpenApiParameter(name="year", type=int, location="query", description="Year"),
        ],
        responses={200: {"type": "array", "items": {"type": "object"}}}
    )
    @action(detail=False, methods=['get'], url_path="top-sellers", permission_classes=[IsDealer])
    def top_sellers(self, request):
        month = request.query_params.get("month")
        year = request.query_params.get("year")

        month_date = parse_month_year(month, year)
        if month and not month_date:
            return Response({"detail": "Invalid month/year."}, status=400)

        sellers = get_top_sellers(month_date)
        return Response(sellers, status=200)

    @extend_schema(
        tags=["Analytics"],
        description="Retrieve cars with the highest sales rate in the specified month.",
        parameters=[
            OpenApiParameter(name="month", type=int, location="query", description="Month (1-12)"),
            OpenApiParameter(name="year", type=int, location="query", description="Year"),
        ],
        responses={200: {"type": "array", "items": {"type": "object"}}}
    )
    @action(detail=False, methods=['get'], url_path="high-sales-cars", permission_classes=[IsDealer])
    def high_sales_rate(self, request):
        month = request.query_params.get("month")
        year = request.query_params.get("year")

        month_date = parse_month_year(month, year)
        if month and not month_date:
            return Response({"detail": "Invalid month/year."}, status=400)

        cars = get_high_sales_rate_cars(month_date)
        return Response(cars, status=200)

    @extend_schema(
        tags=["Analytics"],
        description="View car analytics with optional filters",
        parameters=[
            OpenApiParameter("range", str, description="day | week | month | year"),
            OpenApiParameter("car_id", int, description="Filter by car ID"),
            OpenApiParameter("dealer_id", int, description="Filter by dealer ID"),
            OpenApiParameter("date_from", str, description="YYYY-MM-DD"),
            OpenApiParameter("date_to", str, description="YYYY-MM-DD"),
        ],
    )
    @action(detail=False, methods=["get"], permission_classes=[IsSuperAdminOrAdmin])
    def view_analytics(self, request):

        range_type = request.GET.get("range", "month")
        car_id = request.GET.get("car_id")
        dealer_id = request.GET.get("dealer_id")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        # Time grouping
        trunc_map = {
            "day": TruncDay,
            "week": TruncWeek,
            "year": TruncYear,
            "month": TruncMonth,
        }
        trunc_func = trunc_map.get(range_type, TruncMonth)("viewed_at")

        queryset = CarView.objects.select_related(
            "car",
            "car__dealer",
            "car__make_ref",
            "car__model_ref",
        )

        # ---- Filters ----
        if car_id:
            queryset = queryset.filter(car_id=car_id)

        if dealer_id:
            queryset = queryset.filter(car__dealer_id=dealer_id)

        if date_from:
            queryset = queryset.filter(viewed_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(viewed_at__date__lte=date_to)

        analytics = (
            queryset
            .annotate(
                period=trunc_func,
                make=F("car__make_ref__name"),
                model=F("car__model_ref__name"),
                dealer_id=F("car__dealer_id"),
            )
            .values(
                "car_id",
                "dealer_id",
                "make",
                "model",
                "period",
            )
            .annotate(
                total_views=Count("id"),
                unique_viewers=Count("user", distinct=True),
            )
            .order_by("-period", "-total_views")
        )

        return Response(analytics)

    @extend_schema(
        tags=["Analytics"],
        description="View car viewers analytics with optional filters",
        parameters=[
            OpenApiParameter("car_id", int, description="Filter by car ID"),
            OpenApiParameter("dealer_id", int, description="Filter by dealer ID"),
            OpenApiParameter("date_from", str, description="YYYY-MM-DD"),
            OpenApiParameter("date_to", str, description="YYYY-MM-DD"),
        ],
    )
    @action(detail=False, methods=["get"], permission_classes=[IsSuperAdminOrAdmin])
    def view_viewers(self, request):
        car_id = request.GET.get("car_id")
        dealer_id = request.GET.get("dealer_id")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        queryset = CarView.objects.select_related(
            "user",
            "user__profile",
            "car",
            "car__dealer"
        )

        if car_id:
            queryset = queryset.filter(car_id=car_id)

        if dealer_id:
            queryset = queryset.filter(car__dealer_id=dealer_id)

        if date_from:
            queryset = queryset.filter(viewed_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(viewed_at__date__lte=date_to)

        data = queryset.annotate(
            first_name=Coalesce(
                "user__profile__first_name",
                Value("")
            ),
            last_name=Coalesce(
                "user__profile__last_name",
                Value("")
            ),
            contact=Coalesce(
                "user__profile__contact",
                Value("")
            ),
            viewer_type=Case(
                When(user__isnull=True, then=Value("anonymous")),
                default=Value("registered"),
                output_field=CharField()
            )
        ).values(
            "car_id",
            "user_id",
            "user__email",
            "first_name",
            "last_name",
            "contact",
            "viewed_at",
            "viewer_type",
        ).order_by("-viewed_at")

        return Response(data)

    @extend_schema(
        tags=["Analytics"],
        description="Rating analytics with filters",
        parameters=[
            OpenApiParameter("car_id", int, description="Filter by car ID"),
            OpenApiParameter("dealer_id", int, description="Filter by dealer ID"),
            OpenApiParameter("date_from", str, description="YYYY-MM-DD"),
            OpenApiParameter("date_to", str, description="YYYY-MM-DD"),
        ],
    )
    @action(detail=False, methods=["get"], permission_classes=[IsBuyer])
    def rating_analytics(self, request):

        car_id = request.GET.get("car_id")
        dealer_id = request.GET.get("dealer_id")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        queryset = CarRating.objects.select_related(
            "car",
            "car_dealer",
            "car_make",
            "car_model",
        )

        # ---- Filters ----
        if car_id:
            queryset = queryset.filter(car_id=car_id)

        if dealer_id:
            queryset = queryset.filter(car__dealer_id=dealer_id)

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        analytics = (
            queryset
            .values(
                "car_id",
                "car__dealer_id",
                "car__make_ref__name",
                "car__model_ref__name",
            )
            .annotate(
                average_rating=Avg("rating"),
                total_ratings=Count("id"),
                rating_1=Count("id", filter=Q(rating=1)),
                rating_2=Count("id", filter=Q(rating=2)),
                rating_3=Count("id", filter=Q(rating=3)),
                rating_4=Count("id", filter=Q(rating=4)),
                rating_5=Count("id", filter=Q(rating=5)),

                reviews=ArrayAgg(
                    JSONObject(
                        email=F("user__email"),  # adjust if relation differs
                        rating=F("rating"),
                        comment=F("comment"),
                        created_at=F("created_at"),
                    ),
                    filter=Q(comment__isnull=False),
                    distinct=True,
                ),
            )
            .order_by("-average_rating", "-total_ratings")
        )

        return Response(analytics)

    @extend_schema(
        tags=["Analytics"],
        description="Get analytics for dealers, including detailed views by car make/model.",
        responses={
            200: {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "car_id": {"type": "integer"},
                        "car_make": {"type": "string"},
                        "car_model": {"type": "string"},
                        "total_unique_views": {"type": "integer"},
                        "viewer_emails": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdminOrAdminOrDealer], url_path='dealer-view-analytics')
    def dealer_analytic_views(self, request):
        if not has_role(request.user, ['dealer']):
            return Response(
                {"error": "Only dealers can access this analytics."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            dealer = DealerProfile.objects.get(profile=request.user.profile)

            analytics = (
                CarView.objects.filter(car__dealer=dealer)
                .annotate(
                    c_id=F("car__id"),
                    car_make=F("car__make_ref__name"),
                    car_model=F("car__model_ref__name"),
                )
                .values(
                    "c_id",
                    "car_make",
                    "car_model",
                )
                .annotate(
                    total_unique_views=Count("user", distinct=True),
                    viewer_emails=ArrayAgg("user__email", distinct=True),
                )
                .order_by("-total_unique_views")
            )

            return Response(analytics)

        except DealerProfile.DoesNotExist:
            return Response(
                {"error": "Dealer profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.exception(f"Error in dealer_analytics: {e}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=["Analytics"],
        description="Get view analytics for a broker, showing each car, total unique views, and the list of viewer emails.",
        responses={
            200: OpenApiResponse(
                description="Broker car view analytics",
                response={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "car_id": {"type": "integer"},
                            "car_make": {"type": "string"},
                            "car_model": {"type": "string"},
                            "total_unique_views": {"type": "integer"},
                            "viewer_emails": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                }
            ),
            403: OpenApiResponse(
                description="User is not a broker",
                response={"type": "object", "properties": {"error": {"type": "string"}}}
            ),
            404: OpenApiResponse(
                description="Broker profile not found",
                response={"type": "object", "properties": {"error": {"type": "string"}}}
            )
        }
    )
    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdminOrAdminOrBroker], url_path='broker-view-analytics')
    def broker_analytic_views(self, request):
        if not has_role(request.user, ['broker']):
            return Response(
                {"error": "Only brokers can access this analytics."}, status=status.HTTP_403_FORBIDDEN)
        try:
            broker = BrokerProfile.objects.get(profile=request.user.profile)

            analytics = (
                CarView.objects.filter(car__broker=broker)
                .annotate(
                    c_id=F("car__id"),
                    car_make=F("car__make_ref__name"),
                    car_model=F("car__model_ref__name"),
                )
                .values(
                    "c_id",
                    "car_make",
                    "car_model"
                )
                .annotate(
                    total_unique_views=Count("user", distinct=True),
                    viewer_emails=ArrayAgg("user__email", distinct=True),
                )
                .order_by("-total_unique_views")
            )

            return Response(analytics)

        except BrokerProfile.DoesNotExist:
            return Response(
                {"error": "Broker profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error in broker_analytics: {e}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=["Analytics"],
        description="Get financial analytics for a dealer (expenses, revenue, and profit) by day/week/month/year.",
        parameters=[
            OpenApiParameter(
                name="range",
                description= "Time range for analytics: day, week, month, or year",
                required = False,
                type=str,
                enum =  ["day", "week", "month", "year"],
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "range": {"type": "string"},
                    "total_expenses": {"type": "number"},
                    "total_revenue": {"type": "number"},
                    "net_profit": {"type": "number"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "period": {"type": "string"},
                                "expense": {"type": "number"},
                                "revenue": {"type": "number"},
                                "net_profit": {"type": "number"},
                            }
                        }
                    }
                }
            },
            403: OpenApiResponse(description="Forbidden — Only dealers may access this endpoint"),
        }
    )
    @action(detail=False, methods=['get'], url_path='financial-analytics', permission_classes=[IsDealer])
    def financial_analytics(self, request):
        """Financial analytics for DEALERS only."""
        user = request.user

        if not has_role(user, ['dealer']):
            return Response({"error": "Only dealers have access to financial analytics."}, status=status.HTTP_403_FORBIDDEN)

        # Get dealer profile
        try:
            dealer = DealerProfile.objects.get(profile=user.profile)
        except DealerProfile.DoesNotExist:
            return Response({"error": "Dealer profile not found."}, status=404)

        # Time range
        period = request.GET.get("range", "month")

        trunc_map = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth, "year": TruncYear}

        if period not in trunc_map:
            return Response({"error": "Invalid range. Use day, week, month, or year."}, status=400)

        Trunc = trunc_map[period]

        # EXPENSES = Expense + CarExpense
        general_expenses = (
            Expense.objects.filter(dealer=dealer)
            .annotate(period=Trunc("created_at"))
            .annotate(final_amount=F("amount") * F("exchange_rate"))
            .values("period")
            .annotate(total=Sum("final_amount"))
        )

        car_expenses = (
            CarExpense.objects.filter(dealer=dealer)
            .annotate(period=Trunc("created_at"))
            .values("period")
            .annotate(total=Sum("converted_amount"))
        )

        # Convert both to dict for merging by period
        expense_map = {}

        for row in general_expenses:
            expense_map[row["period"]] = row["total"]

        for row in car_expenses:
            expense_map[row["period"]] = expense_map.get(row["period"], 0) + row["total"]

        # REVENUE (converted)
        revenue_qs = (
            Revenue.objects.filter(dealer=dealer)
            .annotate(period=Trunc("created_at"))
            .values("period")
            .annotate(total=Sum("converted_amount"))
        )

        revenue_map = {r["period"]: r["total"] for r in revenue_qs}

        # Combine into analytics rows
        periods = sorted(set(list(expense_map.keys()) + list(revenue_map.keys())))

        results = []
        total_expenses = 0
        total_revenue = 0

        for p in periods:
            exp = expense_map.get(p, 0)
            rev = revenue_map.get(p, 0)

            total_expenses += exp
            total_revenue += rev

            results.append({
                "period": p.date().strftime("%Y-%m-%d"),
                "expense": round(exp, 2),
                "revenue": round(rev, 2),
                "net_profit": round(rev - exp, 2)
            })

        return Response({
            "range": period,
            "total_expenses": round(total_expenses, 2),
            "total_revenue": round(total_revenue, 2),
            "net_profit": round(total_revenue - total_expenses, 2),
            "results": results
        })

