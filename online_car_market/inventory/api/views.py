import logging
from django.db.models import Avg, Count, Q, Sum, Min, F, Subquery, OuterRef
from django.db import connection
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, mixins
from rest_framework.filters import SearchFilter, OrderingFilter
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes, OpenApiExample, OpenApiResponse
from django.db.models import Count, Avg, Q, F
from ..models import Car, CarMake, CarModel, FavoriteCar, CarView, CarImage
from .serializers import (CarSerializer, VerifyCarSerializer, BidSerializer, CarMakeSerializer, ContactSerializer,
                          CarModelSerializer, FavoriteCarSerializer, CarViewSerializer, CarViewAnalyticsSerializer
                          )
from online_car_market.users.permissions import IsSuperAdminOrAdminOrDealerOrBroker, IsSuperAdminOrAdmin, IsSuperAdminOrAdminOrBuyer
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.payment.models import Payment
from online_car_market.users.models import Profile
from online_car_market.users.permissions import CanPostCar

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

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]   # No authentication required
        return [IsSuperAdminOrAdmin()]   # Only admins for create/update/delete


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

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]   # No authentication required
        return [IsSuperAdminOrAdmin()]   # Only admins for create/update/delete

@extend_schema_view(
list=extend_schema(
        tags=["Dealers - Inventory"],
        description="List all verified cars for any user. Authenticated users with roles (broker, seller, dealer, admin) see additional cars based on their role.",
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
        description="Create a car listing (dealers/brokers/seller/admins only). Brokers must have paid (can_post=True).",
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
    permission_classes = [IsAuthenticatedOrReadOnly & CanPostCar]
    parser_classes = [MultiPartParser, FormParser]
    queryset = Car.objects.all()

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        # Super admin / admin: see everything
        if has_role(user, ['super_admin', 'admin']):
            queryset = queryset.order_by('-priority', '-created_at')

        # --- Dealer: see ONLY their own cars ---
        elif has_role(user, 'dealer'):
            queryset = queryset.filter(
                dealer__profile__user=user
            ).order_by('-priority', '-created_at')

        # Seller: see ONLY cars posted by them under their dealer
        elif has_role(user, 'seller'):
            from online_car_market.dealers.models import DealerStaff
            staff = DealerStaff.objects.filter(user=user, role='seller').first()
            if staff:
                queryset = queryset.filter(
                    dealer=staff.dealer,
                    posted_by=user
                ).order_by('-priority', '-created_at')
            else:
                queryset = queryset.none()  # seller not assigned to any dealer

        # Broker: see ONLY their own cars
        elif has_role(user, 'broker'):
            queryset = queryset.filter(
                broker__profile__user=user
            ).order_by('-priority', '-created_at')

        # --- Buyer or unauthenticated users: see ONLY verified cars ---
        else:
            queryset = queryset.filter(
                verification_status='verified'
            ).order_by('-priority', '-created_at')

        # Optional filter: by broker_email query parameter
        broker_email = self.request.query_params.get('broker_email')
        if broker_email:
            from online_car_market.brokers.models import BrokerProfile
            try:
                broker_profile = BrokerProfile.objects.get(profile__user__email=broker_email)
                queryset = queryset.filter(broker=broker_profile)
            except BrokerProfile.DoesNotExist:
                queryset = queryset.none()

        return queryset

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "bid", "pay", "broker_payment"]:
            return [CanPostCar()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        # 1. Broker role check
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

        # 2. Save main car data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        car = serializer.save()

        # 3. Process uploaded images
        uploaded_images = []
        for key, file in request.FILES.items():
            if key.startswith("uploaded_images"):
                # Example key: uploaded_images[0].image_file
                index = key.split('[')[1].split(']')[0]
                caption = request.data.get(f"uploaded_images[{index}].caption")
                is_featured = request.data.get(f"uploaded_images[{index}].is_featured", "false").lower() == "true"
                uploaded_images.append({
                    "image_file": file,
                    "caption": caption,
                    "is_featured": is_featured
                })

        # 4. Save CarImage instances
        first_image_id = None
        for i, img_data in enumerate(uploaded_images):
            car_image = CarImage.objects.create(
                car=car,
                image=img_data['image_file'],
                caption=img_data['caption'],
                is_featured=img_data['is_featured']
            )
            if i == 0:
                first_image_id = car_image.id

        # 5. Ensure at least one featured image
        if not CarImage.objects.filter(car=car, is_featured=True).exists() and first_image_id:
            first_image = CarImage.objects.get(id=first_image_id)
            first_image.is_featured = True
            first_image.save()

        # 6. Return full car data
        return Response(self.get_serializer(car).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Dealers - Inventory"],
        description="Verify a car listing and set priority (admin/super_admin only).",
        request=VerifyCarSerializer,
        responses={200: VerifyCarSerializer}
    )
    @action(detail=True, methods=['patch'], serializer_class=VerifyCarSerializer,
            parser_classes=[JSONParser, FormParser, MultiPartParser])
    def verify(self, request, pk=None):
        if not has_role(request.user, ['super_admin', 'admin']):
            return Response(
                {"detail": "Only admins can verify cars."},
                status=status.HTTP_403_FORBIDDEN
            )
        car = self.get_object()
        serializer = self.get_serializer(car, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        verification_status = serializer.validated_data.get('verification_status')
        if verification_status is None:
            return Response(
                {"error": "verification_status is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        car.verification_status = verification_status
        car.priority = (car.verification_status == 'verified')
        car.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

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

    ''' @extend_schema(
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
        return Response({"cheap_cars": list(cheap_cars)}) '''

    @extend_schema(
        tags=["Analytics"],
        description="Get car analytics for buyers with cheapest car per make/model.",
    )
    @action(
        detail=False,
        methods=['get'],
        url_path='buyer-analytics',
        permission_classes = [AllowAny]
    )
    def buyer_analytics(self, request):
        # if not has_role(request.user, ['buyer']):
            # return Response({"error": "Only buyers can access this analytics."}, status=403)

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
            featured_images = CarImage.objects.filter(
                car_id__in=cheapest_car_ids,
                is_featured=True
            ).values('car_id', 'image')

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

        car = serializer.validated_data.get("car")
        car_view, created = CarView.objects.update_or_create(
            car=car,
            user=user,
            defaults={"ip_address": ip_address}
        )
        serializer.instance = car_view

    def update(self, request, *args, **kwargs):
        return Response({"error": "Updating views is not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response({"error": "Updating views is not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({"error": "Deleting views is not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdminOrAdminOrDealerOrBroker])
    def analytics(self, request):
        if has_role(request.user, ['super_admin']):
            try:
                analytics = (
                    CarView.objects.values("car__id", "car__make_ref__name", "car__model_ref__name")
                    .annotate(total_views=Count("id"))
                    .order_by("-total_views")
                )

                # Force evaluation safely
                try:
                    analytics_list = list(analytics)
                    logger.debug(f"Raw analytics query result (super_admin): {analytics_list}")
                except Exception as eval_err:
                    logger.exception(f"Error while evaluating analytics queryset: {str(eval_err)}")
                    return Response(
                        {"error": f"Queryset evaluation failed: {str(eval_err)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )

                formatted = [
                    {
                        "car_id": item["car__id"],
                        "car_make": item["car__make_ref__name"],
                        "car_model": item["car__model_ref__name"],
                        "total_views": item["total_views"]
                    }
                    for item in analytics_list
                ]

                serializer = CarViewAnalyticsSerializer(formatted, many=True)
                return Response(serializer.data)

            except Exception as e:
                logger.exception(f"Unexpected error in analytics endpoint: {str(e)}")

                # Optionally dump last SQL query for debugging
                logger.debug(f"Last executed SQL: {connection.queries[-1] if connection.queries else 'No queries'}")

                return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"error": "Only super admins can access this endpoint."}, status=403)

    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdminOrAdminOrDealerOrBroker],
            url_path='dealer-analytics')
    def dealer_analytics(self, request):
        if not has_role(request.user, ['dealer']):
            return Response({"error": "Only dealers can access this analytics."}, status=status.HTTP_403_FORBIDDEN)

        try:
            dealer = DealerProfile.objects.get(profile=request.user.profile)
            logger.info(f"Dealer profile found: {dealer}")

            analytics = (
                CarView.objects.filter(car__dealer=dealer)
                .values("car__id", "car__make_ref__name", "car__model_ref__name")
                .annotate(total_views=Count("id"))
                .order_by("-total_views")
            )

            logger.debug(f"Raw dealer analytics for {dealer}: {list(analytics)}")

            formatted = [
                {
                    "car_id": item["car__id"],
                    "car_make": item["car__make_ref__name"],
                    "car_model": item["car__model_ref__name"],
                    "total_views": item["total_views"]
                }
                for item in analytics
            ]

            serializer = CarViewAnalyticsSerializer(formatted, many=True)
            return Response(serializer.data)

        except DealerProfile.DoesNotExist:
            logger.error(f"Dealer profile not found for user {request.user.id}")
            return Response({"error": "Dealer profile not found."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.exception(f"Unexpected error in dealer_analytics for user {request.user.id}: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], permission_classes=[IsSuperAdminOrAdminOrDealerOrBroker],
            url_path='broker-analytics')
    def broker_analytics(self, request):
        if not has_role(request.user, ['broker']):
            return Response({"error": "Only brokers can access this analytics."}, status=status.HTTP_403_FORBIDDEN)

        try:
            broker = BrokerProfile.objects.get(profile=request.user.profile)
            logger.info(f"Broker profile found: {broker}")

            analytics = (
                CarView.objects.filter(car__broker=broker)
                .values("car__id", "car__make_ref__name", "car__model_ref__name")
                .annotate(total_views=Count("id"))
                .order_by("-total_views")
            )

            logger.debug(f"Raw broker analytics for {broker}: {list(analytics)}")

            formatted = [
                {
                    "car_id": item["car__id"],
                    "car_make": item["car__make_ref__name"],
                    "car_model": item["car__model_ref__name"],
                    "total_views": item["total_views"]
                }
                for item in analytics
            ]

            serializer = CarViewAnalyticsSerializer(formatted, many=True)
            return Response(serializer.data)

        except BrokerProfile.DoesNotExist:
            logger.error(f"Broker profile not found for user {request.user.id}")
            return Response({"error": "Broker profile not found."}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.exception(f"Unexpected error in broker_analytics for user {request.user.id}: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    list=extend_schema(
        tags=["Popular Cars"],
        description="List popular cars based on view count. Accessible to all users, including buyers and unauthenticated users.",
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by car status (pending, verified, rejected)',
                enum=['pending', 'verified', 'rejected']
            ),
            OpenApiParameter(
                name='sale_type',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by sale type (direct, auction)',
                enum=['direct', 'auction']
            ),
            OpenApiParameter(
                name='make_ref',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Filter by car make ID'
            ),
            OpenApiParameter(
                name='min_price',
                type=float,
                location=OpenApiParameter.QUERY,
                description='Filter by minimum price'
            ),
            OpenApiParameter(
                name='max_price',
                type=float,
                location=OpenApiParameter.QUERY,
                description='Filter by maximum price'
            ),
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Search by make, model, or description'
            ),
            OpenApiParameter(
                name='ordering',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Order by views, price, or created_at (prefix with - for descending)',
                enum=['views', '-views', 'price', '-price', 'created_at', '-created_at']
            )
        ],
        responses={
            200: CarSerializer(many=True),
        }
    ),
    retrieve=extend_schema(
        tags=["Popular Cars"],
        description="Retrieve details of a specific popular car. Increments view count. Accessible to all users, including buyers and unauthenticated users.",
        responses={
            200: CarSerializer,
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Car not found.",
                examples=[
                    OpenApiExample("Not Found", value={"detail": "Car not found."})
                ]
            )
        }
    )
)
class PopularCarsViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [AllowAny]  # Public access
    serializer_class = CarSerializer
    queryset = Car.objects.filter(verification_status='verified')  # Only verified cars
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'sale_type', 'make_ref']
    search_fields = ['make', 'model', 'description']
    ordering_fields = ['views', 'price', 'created_at']
    ordering = ['-views']

    def get_queryset(self):
        """
        Return verified cars ordered by view count, with optional filtering.
        """
        queryset = self.queryset

        # Apply additional filters
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        return queryset.order_by('-views')

    def list(self, request, *args, **kwargs):
        """
        List popular cars based on view count with pagination and filtering.
        """
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific car and increment its view count.
        """
        try:
            instance = self.get_object()
            instance.views += 1
            instance.save(update_fields=['views'])
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Car.DoesNotExist:
            return Response(
                {"detail": "Car not found."},
                status=status.HTTP_404_NOT_FOUND
            )


@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Inventory"],
        description="List all contacts (admin-only).",
        responses={200: ContactSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Dealers - Inventory"],
        description=(
            "Retrieve the contact info of the user associated with a specific car, "
            "dealer, or broker. Accessible to authenticated users (buyers) or admins."
        ),
        parameters=[
            OpenApiParameter(
                name="car_id",
                type=int,
                location="path",
                description="ID of the car to get the poster's profile",
                required=False,
            ),
            OpenApiParameter(
                name="dealer_id",
                type=int,
                location="query",
                description="ID of the dealer to get contact info",
                required=False,
            ),
            OpenApiParameter(
                name="broker_id",
                type=int,
                location="query",
                description="ID of the broker to get contact info",
                required=False,
            ),
        ],
        responses={
            200: ContactSerializer,
            404: OpenApiResponse(description="Car, dealer, or broker not found"),
            403: OpenApiResponse(description="Permission denied"),
        },
    ),
)
class ContactViewSet(ReadOnlyModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsSuperAdminOrAdminOrBuyer]

    def list(self, request, *args, **kwargs):
        """Admin-only list of all contacts."""
        user = request.user
        if not (user.is_staff or getattr(user, "is_super_admin", False)):
            return Response(
                {"detail": "Only admins can list all contacts"},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        car_id = kwargs.get("pk")  # From URL path
        dealer_id = request.query_params.get("dealer_id")
        broker_id = request.query_params.get("broker_id")

        # Validate input
        if not any([car_id, dealer_id, broker_id]):
            return Response(
                {"detail": "Please provide car_id, dealer_id, or broker_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if sum(bool(x) for x in [car_id, dealer_id, broker_id]) > 1:
            return Response(
                {"detail": "Please provide only one of car_id, dealer_id, or broker_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Retrieve profile
        if car_id:
            car = get_object_or_404(Car, id=car_id)
            profile = car.posted_by.profile
        elif dealer_id:
            dealer = get_object_or_404(DealerProfile, id=dealer_id)
            profile = dealer.profile
        elif broker_id:
            broker = get_object_or_404(BrokerProfile, id=broker_id)
            profile = broker.profile
        else:
            return Response(
                {"detail": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(profile)
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
