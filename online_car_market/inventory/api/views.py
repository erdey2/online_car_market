import logging
from django.db.models import Avg, Count, Q, Sum
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets, mixins
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiExample, OpenApiResponse
from django.db.models import Count, Avg, Q, F
from ..models import Car, CarMake, CarModel, FavoriteCar, CarView
from .serializers import (CarSerializer, VerifyCarSerializer, BidSerializer, CarMakeSerializer,
                          CarModelSerializer, FavoriteCarSerializer, CarViewSerializer, CarViewAnalyticsSerializer
                          )
from online_car_market.users.permissions import IsSuperAdminOrAdminOrDealerOrBroker, IsSuperAdmin
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.payment.models import Payment

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(
        tags=["Cars - Makes"],
        description="List all car makes."
    ),
    retrieve=extend_schema(
        tags=["Cars - Makes"],
        description="Retrieve details of a specific car make."
    ),
    create=extend_schema(
        tags=["Cars - Makes"],
        description="Create a new car make (admin only)."
    ),
    update=extend_schema(
        tags=["Cars - Makes"],
        description="Update an existing car make (admin only)."
    ),
    partial_update=extend_schema(
        tags=["Cars - Makes"],
        description="Partially update a car make (admin only)."
    ),
    destroy=extend_schema(
        tags=["Cars - Makes"],
        description="Delete a car make (admin only)."
    ),
)
class CarMakeViewSet(ModelViewSet):
    queryset = CarMake.objects.all()
    serializer_class = CarMakeSerializer

@extend_schema_view(
    list=extend_schema(
        tags=["Cars - Models"],
        description="List all car models."
    ),
    retrieve=extend_schema(
        tags=["Cars - Models"],
        description="Retrieve details of a specific car model."
    ),
    create=extend_schema(
        tags=["Cars - Models"],
        description="Create a new car model (admin only)."
    ),
    update=extend_schema(
        tags=["Cars - Models"],
        description="Update an existing car model (admin only)."
    ),
    partial_update=extend_schema(
        tags=["Cars - Models"],
        description="Partially update a car model (admin only)."
    ),
    destroy=extend_schema(
        tags=["Cars - Models"],
        description="Delete a car model (admin only)."
    ),
)
class CarModelViewSet(ModelViewSet):
    queryset = CarModel.objects.select_related('make').all()
    serializer_class = CarModelSerializer


@extend_schema_view(
list=extend_schema(
        tags=["Dealers - Inventory"],
        description="List all verified cars for any user. Authenticated users with roles (broker, dealer, admin) see additional cars based on their role.",
        parameters=[
            OpenApiParameter(
                name='broker_email',
                type=str,
                location='query',
                description='Filter cars by broker email address.',
                required=False
            ),
        ],
        responses={
            200: CarSerializer(many=True),
        }
    ),
    retrieve=extend_schema(
        tags=["Dealers - Inventory"],
        description="Retrieve a specific verified car for any user. Authenticated users with roles can access additional cars.",
        responses={
            200: CarSerializer,
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Car not found or not accessible.",
                examples=[OpenApiExample("Not Found", value={"detail": "Not found."})]
            )
        }
    ),
    create=extend_schema(
        tags=["Dealers - Inventory"],
        description="Create a car listing (dealers/brokers/admins only). Brokers must have paid (can_post=True).",
        request=CarSerializer,
        responses={201: CarSerializer}
    ),
    update=extend_schema(
        tags=["Dealers - Inventory"],
        description="Update a car listing (dealers/brokers/admins only).",
        request=CarSerializer,
        responses={200: CarSerializer}
    ),
    partial_update=extend_schema(
        tags=["Dealers - Inventory"],
        description="Partially update a car listing.",
        request=CarSerializer,
        responses={200: CarSerializer}
    ),
    destroy=extend_schema(
        tags=["Dealers - Inventory"],
        description="Delete a car listing (dealers/brokers/admins only).",
        responses={204: None}
    ),
)
class CarViewSet(viewsets.ModelViewSet):
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    queryset = Car.objects.all()

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        # Apply role-based filtering
        if has_role(user, ['super_admin', 'admin']):
            queryset = queryset.order_by('-priority', '-created_at')
        elif has_role(user, 'dealer'):
            queryset = queryset.filter(
                Q(dealer__profile__user=user) | Q(verification_status='verified')
            ).order_by('-priority', '-created_at')
        elif has_role(user, 'broker'):
            queryset = queryset.filter(
                Q(broker__profile__user=user) | Q(verification_status='verified')
            ).order_by('-priority', '-created_at')
        else:  # buyer or unauthenticated
            queryset = queryset.filter(verification_status='verified').order_by('-priority', '-created_at')

        # Filter by broker_email query parameter
        broker_email = self.request.query_params.get('broker_email')
        if broker_email:
            try:
                broker_profile = BrokerProfile.objects.get(profile__user__email=broker_email)
                queryset = queryset.filter(broker=broker_profile)
            except BrokerProfile.DoesNotExist:
                queryset = queryset.none()
        return queryset

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "bid", "pay", "broker_payment"]:
            return [IsSuperAdminOrAdminOrDealerOrBroker()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        if has_role(request.user, 'broker'):
            try:
                broker_profile = BrokerProfile.objects.get(profile__user=request.user)
                if not broker_profile.can_post:
                    return Response(
                        {"detail": "Broker must complete payment to post cars."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except BrokerProfile.DoesNotExist:
                return Response(
                    {"detail": "Broker profile not found."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        car = serializer.save()
        return Response(self.get_serializer(car).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Dealers - Inventory"],
        description="Verify a car listing and set priority (admin/super_admin only).",
        request=VerifyCarSerializer,
        responses={200: VerifyCarSerializer}
    )
    @action(detail=True, methods=['patch'], serializer_class=VerifyCarSerializer)
    def verify(self, request, pk=None):
        if not has_role(request.user, ['super_admin', 'admin']):
            return Response(
                {"detail": "Only admins can verify cars."},
                status=status.HTTP_403_FORBIDDEN
            )
        car = self.get_object()
        serializer = self.get_serializer(car, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        car.verification_status = serializer.validated_data['verification_status']
        car.priority = (car.verification_status == 'verified')
        car.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Dealers - Inventory"],
        parameters=[
            OpenApiParameter(name="fuel_type", type=OpenApiTypes.STR, location="query", description="Fuel type (electric, hybrid, petrol, diesel)"),
            OpenApiParameter(name="price_min", type=OpenApiTypes.FLOAT, location="query", description="Minimum price"),
            OpenApiParameter(name="price_max", type=OpenApiTypes.FLOAT, location="query", description="Maximum price"),
            OpenApiParameter(name="sale_type", type=OpenApiTypes.STR, location="query", description="Sale type (fixed_price, auction)"),
            OpenApiParameter(name="make_ref", type=OpenApiTypes.INT, location="query", description="Car make ID"),
            OpenApiParameter(name="model_ref", type=OpenApiTypes.INT, location="query", description="Car model ID"),
            OpenApiParameter(name="make", type=OpenApiTypes.STR, location="query", description="Car make name"),
            OpenApiParameter(name="model", type=OpenApiTypes.STR, location="query", description="Car model name"),
        ],
        description="Filter verified cars by fuel type, price range, sale type, make, or model, with verified cars prioritized.",
        responses={200: CarSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], serializer_class=CarSerializer)
    def filter(self, request):
        queryset = self.get_queryset()
        fuel_type = request.query_params.get('fuel_type')
        price_min = request.query_params.get('price_min')
        price_max = request.query_params.get('price_max')
        sale_type = request.query_params.get('sale_type')
        make_ref = request.query_params.get('make_ref')
        model_ref = request.query_params.get('model_ref')
        make = request.query_params.get('make')
        model = request.query_params.get('model')

        valid_fuel_types = [choice[0] for choice in Car.FUEL_TYPES]
        if fuel_type and fuel_type not in valid_fuel_types:
            return Response(
                {"error": f"Invalid fuel type. Must be one of: {', '.join(valid_fuel_types)}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        valid_sale_types = [choice[0] for choice in Car.SALE_TYPES]
        if sale_type and sale_type not in valid_sale_types:
            return Response(
                {"error": f"Invalid sale type. Must be one of: {', '.join(valid_sale_types)}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if fuel_type:
            queryset = queryset.filter(fuel_type=fuel_type)
        if make_ref:
            try:
                make_ref = int(make_ref)
                if not CarMake.objects.filter(id=make_ref).exists():
                    return Response({"error": "Invalid make ID."}, status=status.HTTP_400_BAD_REQUEST)
                queryset = queryset.filter(make_ref=make_ref)
            except ValueError:
                return Response({"error": "Make ID must be a valid integer."}, status=status.HTTP_400_BAD_REQUEST)
        if model_ref:
            try:
                model_ref = int(model_ref)
                if not CarModel.objects.filter(id=model_ref).exists():
                    return Response({"error": "Invalid model ID."}, status=status.HTTP_400_BAD_REQUEST)
                queryset = queryset.filter(model_ref=model_ref)
            except ValueError:
                return Response({"error": "Model ID must be a valid integer."}, status=status.HTTP_400_BAD_REQUEST)
        if make:
            if not CarMake.objects.filter(name__iexact=make).exists():
                return Response({"error": "Invalid make name."}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(Q(make=make) | Q(make_ref__name__iexact=make))
        if model:
            if not CarModel.objects.filter(name__iexact=model).exists():
                return Response({"error": "Invalid model name."}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(Q(model=model) | Q(model_ref__name__iexact=model))
        try:
            if price_min:
                price_min = float(price_min)
                if price_min < 0:
                    return Response({"error": "Minimum price cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
                queryset = queryset.filter(price__gte=price_min)
            if price_max:
                price_max = float(price_max)
                if price_max < 0:
                    return Response({"error": "Maximum price cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
                if price_min and price_max < price_min:
                    return Response(
                        {"error": "Maximum price cannot be less than minimum price."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                queryset = queryset.filter(price__lte=price_max)
        except ValueError:
            return Response({"error": "Price parameters must be valid numbers."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Dealers - Inventory"],
        description="Place a bid on an auction car.",
        request=BidSerializer,
        responses={201: BidSerializer}
    )
    @action(detail=True, methods=['post'], serializer_class=BidSerializer)
    def bid(self, request, pk=None):
        car = self.get_object()
        if car.sale_type != 'auction':
            return Response(
                {"detail": "Bids can only be placed on auction cars."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        bid = serializer.save(car=car)
        return Response(BidSerializer(bid).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Analytics"],
        description="Get market analytics (super admin only).",
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
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        if not has_role(request.user, ['super_admin']):
            return Response({"error": "Only super admins can access analytics."}, status=status.HTTP_403_FORBIDDEN)
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
            broker_name = F('profile__user__email')
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
        description="Get cheap cars for buyers.",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "cheap_cars": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "make_name": {"type": "string"},
                                "price": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'], url_path='buyer-analytics')
    def buyer_analytics(self, request):
        if not has_role(request.user, ['buyer']):
            return Response({"error": "Only buyers can access this analytics."}, status=status.HTTP_403_FORBIDDEN)

        cheap_cars = (
            Car.objects.exclude(status='sold')
            .filter(price__isnull=False, verification_status='verified')
            .annotate(make_name=F('make_ref__name'))  # alias
            .order_by('price')[:10]
            .values('id', 'make_name', 'price')
        )
        return Response({"cheap_cars": list(cheap_cars)})

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
    @action(detail=False, methods=['get'], url_path='broker-analytics')
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
        total_money_made = broker.cars.filter(status='sold', price__isnull=False).aggregate(Sum('price'))['price__sum'] or 0
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
    @action(detail=False, methods=['get'], url_path='dealer-analytics')
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
        ).annotate(
            total_sold=Count('id'),
            total_sales=Sum('price'),
            avg_price=Avg('price')
        ).order_by('-total_sold')
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


@extend_schema_view(
    list=extend_schema(
        tags=["User Cars"],
        description="List all cars belonging to the authenticated dealer or broker. User must have the dealer or broker role.",
        responses={
            200: CarSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have the dealer or broker role.",
                examples=[
                    OpenApiExample("Forbidden", value={"detail": "User does not have dealer or broker role."})
                ]
            )
        }
    ),
    retrieve=extend_schema(
        tags=["User Cars"],
        description="Retrieve a specific car. User must have the dealer or broker role and the car must belong to them.",
        responses={
            200: CarSerializer,
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have the dealer or broker role.",
                examples=[
                    OpenApiExample("Forbidden", value={"detail": "User does not have dealer or broker role."})
                ]
            ),
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Car not found or user does not have permission to view it.",
                examples=[
                    OpenApiExample("Not Found",
                                   value={"detail": "Car not found or you do not have permission to view it."})
                ]
            )
        }
    )
)
class UserCarsViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = CarSerializer
    queryset = Car.objects.all()

    def get_queryset(self):
        """
        Filter cars to only show those belonging to the authenticated dealer or broker.
        """
        user = self.request.user
        if not has_role(user, ['dealer', 'broker']):
            return Car.objects.none()

        try:
            if has_role(user, 'dealer'):
                dealer = DealerProfile.objects.get(profile__user=user)
                return self.queryset.filter(dealer=dealer)
            elif has_role(user, 'broker'):
                broker = BrokerProfile.objects.get(profile__user=user)
                return self.queryset.filter(broker=broker)
        except (DealerProfile.DoesNotExist, BrokerProfile.DoesNotExist):
            return Car.objects.none()

        return Car.objects.none()

    def list(self, request, *args, **kwargs):
        """
        List all cars for the authenticated dealer or broker.
        """
        if not has_role(request.user, ['dealer', 'broker']):
            return Response(
                {"detail": "User does not have dealer or broker role."},
                status=status.HTTP_403_FORBIDDEN
            )

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific car. Only accessible if the car belongs to the authenticated dealer or broker.
        """
        if not has_role(request.user, ['dealer', 'broker']):
            return Response(
                {"detail": "User does not have dealer or broker role."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Get the car from the filtered queryset to ensure permission
            car = self.get_queryset().get(pk=kwargs['pk'])
            serializer = self.get_serializer(car)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Car.DoesNotExist:
            return Response(
                {"detail": "Car not found or you do not have permission to view it."},
                status=status.HTTP_404_NOT_FOUND)
        except (DealerProfile.DoesNotExist, BrokerProfile.DoesNotExist):
            return Response(
                {"detail": "User profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )


@extend_schema_view(
    list=extend_schema(
        tags=["Favorites"],
        description="List all favorite cars for the authenticated user. User must have the buyer role.",
        responses={
            200: FavoriteCarSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have the buyer role.",
                examples=[
                    OpenApiExample("Forbidden", value={"detail": "User does not have buyer role."})
                ]
            )
        }
    ),
    create=extend_schema(
        tags=["Favorites"],
        description="Add a car to the user's favorites. User must have the buyer role.",
        request=FavoriteCarSerializer,
        responses={
            201: FavoriteCarSerializer,
            400: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Invalid input, e.g., missing or invalid car_id.",
                examples=[
                    OpenApiExample("Invalid input", value={"detail": "Invalid car_id"})
                ]
            ),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have the buyer role.",
                examples=[
                    OpenApiExample("Forbidden", value={"detail": "User does not have buyer role."})
                ]
            )
        }
    ),
    retrieve=extend_schema(
        tags=["Favorites"],
        description="Retrieve a specific favorite car entry. User must be the owner and have the buyer role.",
        responses={
            200: FavoriteCarSerializer,
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have the buyer role.",
                examples=[
                    OpenApiExample("Forbidden", value={"detail": "User does not have buyer role."})
                ]
            ),
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Favorite car not found or user does not have permission.",
                examples=[
                    OpenApiExample("Not Found", value={"detail": "Favorite car not found or you do not have permission to view it."})
                ]
            )
        }
    ),
    destroy=extend_schema(
        tags=["Favorites"],
        description="Remove a car from the user's favorites. User must be the owner and have the buyer role.",
        responses={
            204: None,
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have the buyer role.",
                examples=[
                    OpenApiExample("Forbidden", value={"detail": "User does not have buyer role."})
                ]
            ),
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Favorite car not found or user does not have permission.",
                examples=[
                    OpenApiExample("Not Found", value={"detail": "Favorite car not found or you do not have permission to delete it."})
                ]
            )
        }
    )
)
class FavoriteCarViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteCarSerializer
    queryset = FavoriteCar.objects.all()

    def get_queryset(self):
        # Restrict to favorites by the authenticated user
        return self.queryset.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            favorite = self.get_queryset().get(pk=kwargs['pk'])
            serializer = self.get_serializer(favorite)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except FavoriteCar.DoesNotExist:
            return Response(
                {"detail": "Favorite car not found or you do not have permission to view it."},
                status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            favorite = self.get_queryset().get(pk=kwargs['pk'])
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except FavoriteCar.DoesNotExist:
            return Response(
                {"detail": "Favorite car not found or you do not have permission to delete it."},
                status=status.HTTP_404_NOT_FOUND
            )

@extend_schema_view(
    create=extend_schema(
        tags=["Car Views"],
        description="Create a car view record for a specific car. Records the user (if authenticated) or IP address (if anonymous).",
        request=CarViewSerializer,
        responses={
            201: CarViewSerializer,
            400: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Invalid input, e.g., missing or invalid car_id.",
                examples=[
                    OpenApiExample("Invalid car_id", value={"error": "Invalid car_id"})
                ]
            )
        }
    ),
    list=extend_schema(
        tags=["Car Views"],
        description="List all car view records. Typically restricted to super admins or users with specific permissions.",
        responses={
            200: CarViewSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="User lacks permission to access this endpoint.",
                examples=[
                    OpenApiExample("Forbidden", value={"error": "You do not have permission to perform this action."})
                ]
            )
        }
    ),
    retrieve=extend_schema(
        tags=["Car Views"],
        description="Retrieve a specific car view record by ID. Typically restricted to super admins or users with specific permissions.",
        responses={
            200: CarViewSerializer,
            403: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="User lacks permission to access this endpoint.",
                examples=[
                    OpenApiExample("Forbidden", value={"error": "You do not have permission to perform this action."})
                ]
            ),
            404: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Car view not found.",
                examples=[
                    OpenApiExample("Not Found", value={"error": "Not found."})
                ]
            )
        }
    ),
    update=extend_schema(
        tags=["Car Views"],
        description="Updating car view records is not allowed.",
        responses={
            405: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Method not allowed.",
                examples=[
                    OpenApiExample("Method Not Allowed", value={"error": "Updating views is not allowed."})
                ]
            )
        }
    ),
    partial_update=extend_schema(
        tags=["Car Views"],
        description="Partially updating car view records is not allowed.",
        responses={
            405: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Method not allowed.",
                examples=[
                    OpenApiExample("Method Not Allowed", value={"error": "Updating views is not allowed."})
                ]
            )
        }
    ),
    destroy=extend_schema(
        tags=["Car Views"],
        description="Deleting car view records is not allowed.",
        responses={
            405: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Method not allowed.",
                examples=[
                    OpenApiExample("Method Not Allowed", value={"error": "Deleting views is not allowed."})
                ]
            )
        }
    ),
    analytics=extend_schema(
        tags=["Analytics"],
        description="Retrieve car view analytics for all cars, showing total views per car. Accessible only to super admins.",
        responses={
            200: CarViewAnalyticsSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="User is not a super admin.",
                examples=[
                    OpenApiExample("Forbidden", value={"error": "Only super admins can access this endpoint."})
                ]
            )
        }
    ),
    dealer_analytics=extend_schema(
        tags=["Analytics"],
        description="Retrieve car view analytics for cars associated with the requesting dealer, showing total views per car.",
        responses={
            200: CarViewAnalyticsSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="User is not a dealer.",
                examples=[
                    OpenApiExample("Forbidden", value={"error": "Only dealers can access this analytics."})
                ]
            ),
            404: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Dealer profile not found.",
                examples=[
                    OpenApiExample("Not Found", value={"error": "Dealer profile not found."})
                ]
            )
        }
    ),
    broker_analytics=extend_schema(
        tags=["Analytics"],
        description="Retrieve car view analytics for cars associated with the requesting broker, showing total views per car.",
        responses={
            200: CarViewAnalyticsSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="User is not a broker.",
                examples=[
                    OpenApiExample("Forbidden", value={"error": "Only brokers can access this analytics."})
                ]
            ),
            404: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Broker profile not found.",
                examples=[
                    OpenApiExample("Not Found", value={"error": "Broker profile not found."})
                ]
            )
        }
    )
)
class CarViewViewSet(viewsets.ModelViewSet):
    queryset = CarView.objects.all()
    serializer_class = CarViewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    http_method_names = ['get', 'post']  # Restrict to GET and POST only

    def perform_create(self, serializer):
        ip_address = self.request.META.get('REMOTE_ADDR')
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user, ip_address=ip_address)

    def update(self, request, *args, **kwargs):
        return Response({"error": "Updating views is not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response({"error": "Updating views is not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({"error": "Deleting views is not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdminOrAdminOrDealerOrBroker])
    def analytics(self, request):
        if has_role(request.user, ['super_admin']):
            analytics = CarView.objects.values('car__id', 'car__make__name').annotate(
                total_views=Count('id')
            ).order_by('-total_views')
            serializer = CarViewAnalyticsSerializer(analytics, many=True)
            return Response(serializer.data)
        return Response({"error": "Only super admins can access this endpoint."}, status=403)

    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdminOrAdminOrDealerOrBroker], url_path='dealer-analytics')
    def dealer_analytics(self, request):
        if not has_role(request.user, ['dealer']):
            return Response({"error": "Only dealers can access this analytics."}, status=403)
        try:
            dealer = DealerProfile.objects.get(user=request.user)
        except DealerProfile.DoesNotExist:
            return Response({"error": "Dealer profile not found."}, status=404)
        analytics = CarView.objects.filter(car__dealer=dealer).values('car__id', 'car__make__name').annotate(
            total_views=Count('id')
        ).order_by('-total_views')
        serializer = CarViewAnalyticsSerializer(analytics, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdminOrAdminOrDealerOrBroker], url_path='broker-analytics')
    def broker_analytics(self, request):
        if not has_role(request.user, ['broker']):
            return Response({"error": "Only brokers can access this analytics."}, status=403)
        try:
            broker = BrokerProfile.objects.get(user=request.user)
        except BrokerProfile.DoesNotExist:
            return Response({"error": "Broker profile not found."}, status=404)
        analytics = CarView.objects.filter(car__broker=broker).values('car__id', 'car__make__name').annotate(
            total_views=Count('id')
        ).order_by('-total_views')
        serializer = CarViewAnalyticsSerializer(analytics, many=True)
        return Response(serializer.data)

# CarImage ViewSet
'''
@extend_schema_view(
    list=extend_schema(tags=["Dealers - Inventory"], description="List all car images."),
    retrieve=extend_schema(tags=["Dealers - Inventory"], description="Retrieve a specific car image."),
    create=extend_schema(tags=["Dealers - Inventory"], description="Create a car image (dealers/admins only)."),
    update=extend_schema(tags=["Dealers - Inventory"], description="Update a car image (dealers/admins only)."),
    partial_update=extend_schema(tags=["Dealers - Inventory"], description="Partially update a car image (dealers/admins only)."),
    destroy=extend_schema(tags=["Dealers - Inventory"], description="Delete a car image (dealers/admins only)."),
)
class CarImageViewSet(ModelViewSet):
    queryset = CarImage.objects.all()
    serializer_class = CarImageSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsSuperAdminOrAdminOrDealer()]
        return super().get_permissions() '''
