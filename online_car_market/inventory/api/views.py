from django.db.models import Count, Avg
from django.db import models
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from ..models import Car, CarImage, Bid, Payment, CarMake, CarModel
from .serializers import CarSerializer, CarImageSerializer, VerifyCarSerializer, BidSerializer, PaymentSerializer
from online_car_market.users.permissions import IsSuperAdminOrAdminOrDealer
from online_car_market.dealers.models import Dealer

# Car ViewSet
@extend_schema_view(
    list=extend_schema(tags=["Dealers - Inventory"], description="List all verified cars for non-admins or all cars for admins."),
    retrieve=extend_schema(tags=["Dealers - Inventory"], description="Retrieve a specific car if verified or user is admin."),
    create=extend_schema(tags=["Dealers - Inventory"], description="Create a car listing (dealers/brokers/admins only)."),
    update=extend_schema(tags=["Dealers - Inventory"], description="Update a car listing (dealers/brokers/admins only)."),
    partial_update=extend_schema(tags=["Dealers - Inventory"], description="Partially update a car listing."),
    destroy=extend_schema(tags=["Dealers - Inventory"], description="Delete a car listing (dealers/brokers/admins only)."),
)
class CarViewSet(ModelViewSet):
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return Car.objects.all()
        return Car.objects.filter(verification_status='verified')

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy",  "bid", "pay"]:
            return [IsSuperAdminOrAdminOrDealer()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        car = serializer.save()
        return Response(self.get_serializer(car).data, status=status.HTTP_201_CREATED)

    # upload-images
    @extend_schema(
        tags=["Dealers - Inventory"],
        description="Upload additional images to an existing car. Use form field `images`.",
        request={
            "multipart/form-data": {
                "type": "object",
                "properties": {
                    "images": {
                        "type": "array",
                        "items": {"type": "string", "format": "binary"}
                    }
                },
                "required": ["images"]
            }
        },
        responses=CarImageSerializer(many=True),
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='upload-images',
        serializer_class=CarImageSerializer,
        parser_classes=[MultiPartParser]
    )
    def upload_images(self, request, pk=None):
        car = self.get_object()
        files = request.FILES.getlist('images')
        if not files:
            return Response(
                {"detail": "No files provided. Use form field name 'images'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        created = []
        for f in files:
            ser = CarImageSerializer(data={'car': car.pk, 'image_file': f}, context={'request': request})
            ser.is_valid(raise_exception=True)
            ser.save()
            created.append(ser.data)
        return Response(created, status=status.HTTP_201_CREATED)

    # verify
    @extend_schema(
        tags=["Dealers - Inventory"],
        description="Verify a car listing (admin/super_admin only).",
        responses=VerifyCarSerializer,
    )
    @action(
        detail=True,
        methods=['patch'],
        serializer_class=VerifyCarSerializer,
        permission_classes=[IsSuperAdminOrAdminOrDealer]
    )
    def verify(self, request, pk=None):
        car = self.get_object()
        serializer = self.get_serializer(car, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    # filter
    @extend_schema(
        tags=["Dealers - Inventory"],
        parameters=[
            OpenApiParameter("fuel_type", OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description="Fuel type (electric, hybrid, petrol, diesel)"),
            OpenApiParameter("price_min", OpenApiTypes.FLOAT, OpenApiParameter.QUERY, description="Minimum price"),
            OpenApiParameter("price_max", OpenApiTypes.FLOAT, OpenApiParameter.QUERY, description="Maximum price"),
            OpenApiParameter(name='sale_type', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY,
                             description='Sale type (fixed_price, auction)'),
            OpenApiParameter(name='make_ref', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY,
                             description='Car make ID'),
            OpenApiParameter(name='model_ref', type=OpenApiTypes.INT, location=OpenApiParameter.QUERY,
                             description='Car model ID'),
        ],
        description="Filter verified cars by fuel type, price range, sale type, make, or model.",
        responses=CarSerializer(many=True),
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
            return Response({"error": f"Invalid fuel type. Must be one of: {', '.join(valid_fuel_types)}."}, status=400)

        valid_sale_types = [choice[0] for choice in Car.SALE_TYPES]
        if sale_type and sale_type not in valid_sale_types:
            return Response({"error": f"Invalid sale type. Must be one of: {', '.join(valid_sale_types)}."}, status=400)

        if fuel_type:
            queryset = queryset.filter(fuel_type=fuel_type)
        if make_ref:
            try:
                make_ref = int(make_ref)
                if not CarMake.objects.filter(id=make_ref).exists():
                    return Response({"error": "Invalid make ID."}, status=400)
                queryset = queryset.filter(make_ref=make_ref)
            except ValueError:
                return Response({"error": "Make ID must be a valid integer."}, status=400)
        if model_ref:
            try:
                model_ref = int(model_ref)
                if not CarModel.objects.filter(id=model_ref).exists():
                    return Response({"error": "Invalid model ID."}, status=400)
                queryset = queryset.filter(model_ref=model_ref)
            except ValueError:
                return Response({"error": "Model ID must be a valid integer."}, status=400)

        if make:
            queryset = queryset.filter(Q(make=make) | Q(make_ref__name=make))
        if model:
            queryset = queryset.filter(Q(model=model) | Q(model_ref__name=model))

        try:
            if price_min:
                price_min = float(price_min)
                if price_min < 0:
                    return Response({"error": "Minimum price cannot be negative."}, status=400)
                queryset = queryset.filter(price__gte=price_min)
            if price_max:
                price_max = float(price_max)
                if price_max < 0:
                    return Response({"error": "Maximum price cannot be negative."}, status=400)
                if price_min and price_max < price_min:
                    return Response({"error": "Maximum price cannot be less than minimum price."}, status=400)
                queryset = queryset.filter(price__lte=price_max)
        except ValueError:
            return Response({"error": "Price parameters must be valid numbers."}, status=400)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Dealers - Inventory"],
        description="Place a bid on an auction car.",
        responses=BidSerializer
    )
    @action(detail=True, methods=['post'], serializer_class=BidSerializer)
    def bid(self, request, pk=None):
        car = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        bid = serializer.save(car=car)
        return Response(BidSerializer(bid).data)

    @extend_schema(
        tags=["Dealers - Inventory"],
        description="Record a payment (listing fee, commission, or purchase).",
        responses=PaymentSerializer
    )
    @action(detail=True, methods=['post'], serializer_class=PaymentSerializer)
    def pay(self, request, pk=None):
        car = self.get_object() if pk else None
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save(user=request.user, car=car)
        return Response(PaymentSerializer(payment).data)

    @extend_schema(
        tags=["Dealers - Inventory"],
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
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        if not has_role(request.user, ['super_admin']):
            return Response({"error": "Only super admins can access analytics."}, status=403)
        total_cars = Car.objects.count()
        average_price = Car.objects.filter(price__isnull=False).aggregate(Avg('price'))['price__avg'] or 0
        dealer_stats = Dealer.objects.annotate(
            total_cars=Count('cars'),
            sold_cars=Count('cars', filter=models.Q(cars__status='sold')),
            avg_price=Avg('cars__price')
        ).values('id', 'name', 'total_cars', 'sold_cars', 'avg_price')
        return Response({
            "total_cars": total_cars,
            "average_price": round(average_price, 2),
            "dealer_stats": list(dealer_stats)
        })

# CarImage ViewSet
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
        return super().get_permissions()
