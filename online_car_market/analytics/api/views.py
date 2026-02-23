import logging
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.users.permissions.drf_permissions import (IsSuperAdminOrAdminOrDealer, IsSuperAdminOrAdminOrBroker,
                                                                 IsSuperAdminOrAdmin, IsDealer, IsBuyer)
from ..utils import get_top_sellers, get_high_sales_rate_cars, parse_month_year
from ..services.platform_service import PlatformAnalyticsService
from ..services.buyer_service import BuyerAnalyticsService
from ..services.broker_service import BrokerAnalyticsService
from ..services.dealer_service import DealerAnalyticsService
from ..services.view_service import CarViewAnalyticsService
from ..services.rating_service import RatingAnalyticsService
from ..services.financial_service import FinancialAnalyticsService

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
    @action(detail=False, methods=['get'], url_path="platform-analytics",
            permission_classes=[IsSuperAdminOrAdmin])
    def analytics(self, request):

        if not has_role(request.user, ['super_admin', 'admin']):
            return Response(
                {"error": "Only super admin or admin can access this analytics."},
                status=status.HTTP_403_FORBIDDEN
            )

        data = PlatformAnalyticsService.get_platform_analytics()
        return Response(data)

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
    @action(detail=False, methods=['get'], url_path='buyer-analytics', permission_classes=[AllowAny])
    def buyer_analytics(self, request):

        data = BuyerAnalyticsService.get_buyer_analytics()
        return Response(data)

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
    @action(detail=False, methods=["get"], url_path="broker-analytics", permission_classes=[IsAuthenticated])
    def broker_analytics(self, request):
        """
        Broker analytics endpoint.
        """
        # Ensure the user has the broker role
        if not has_role(request.user, ["broker"]):
            return Response(
                {"error": "Only brokers can access this analytics."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            broker = BrokerProfile.objects.get(profile=request.user.profile)
        except BrokerProfile.DoesNotExist:
            return Response({"error": "Broker profile not found."}, status=status.HTTP_404_NOT_FOUND)

        data = BrokerAnalyticsService.get_broker_analytics(broker)
        return Response(data)

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
            return Response({"error": "Only dealers can access this analytics."},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            dealer = DealerProfile.objects.get(profile__user=request.user)
        except DealerProfile.DoesNotExist:
            return Response({"error": "Dealer profile not found."}, status=404)

        data = DealerAnalyticsService.get_dealer_analytics(dealer)
        return Response(data)

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

        filters = {
            "range": request.GET.get("range", "month"),
            "car_id": request.GET.get("car_id"),
            "dealer_id": request.GET.get("dealer_id"),
            "date_from": request.GET.get("date_from"),
            "date_to": request.GET.get("date_to"),
        }

        data = CarViewAnalyticsService.get_view_analytics(filters)
        return Response(data)

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
    @action(detail=False, methods=["get"],
            permission_classes=[IsSuperAdminOrAdmin])
    def view_viewers(self, request):

        filters = {
            "car_id": request.GET.get("car_id"),
            "dealer_id": request.GET.get("dealer_id"),
            "date_from": request.GET.get("date_from"),
            "date_to": request.GET.get("date_to"),
        }

        data = CarViewAnalyticsService.get_view_viewers(filters)
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
    @action(detail=False, methods=["get"],
            permission_classes=[IsBuyer])
    def rating_analytics(self, request):

        filters = {
            "car_id": request.GET.get("car_id"),
            "dealer_id": request.GET.get("dealer_id"),
            "date_from": request.GET.get("date_from"),
            "date_to": request.GET.get("date_to"),
        }

        data = RatingAnalyticsService.get_rating_analytics(filters)
        return Response(data)

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
    @action(detail=False, methods=['get'],
            permission_classes=[IsSuperAdminOrAdminOrDealer],
            url_path='dealer-view-analytics')
    def dealer_analytic_views(self, request):

        try:
            dealer = DealerProfile.objects.get(profile=request.user.profile)
        except DealerProfile.DoesNotExist:
            return Response({"error": "Dealer profile not found."}, status=404)

        data = CarViewAnalyticsService.get_dealer_view_analytics(dealer)
        return Response(data)

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

        try:
            broker = BrokerProfile.objects.get(profile=request.user.profile)
        except BrokerProfile.DoesNotExist:
            return Response({"error": "Broker profile not found."}, status=404)

        data = CarViewAnalyticsService.get_broker_view_analytics(broker)
        return Response(data)

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
        user = request.user

        # Ensure user has a profile
        if not hasattr(user, "profile"):
            return Response({"error": "User has no profile."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            dealer = DealerProfile.objects.get(profile=user.profile)
        except DealerProfile.DoesNotExist:
            return Response({"error": "Dealer profile not found."}, status=status.HTTP_404_NOT_FOUND)

        period = request.GET.get("range", "month")
        data = FinancialAnalyticsService.get_financial_analytics(dealer=dealer, period=period)
        return Response(data)


