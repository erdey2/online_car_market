from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from ..models import Car, CarImage
from .serializers import CarSerializer, CarImageSerializer, VerifyCarSerializer
from ..permissions import IsSuperAdminOrAdminOrDealer


# Car ViewSet
@extend_schema_view(
    list=extend_schema(tags=["Dealers - Inventory"]),
    retrieve=extend_schema(tags=["Dealers - Inventory"]),
    create=extend_schema(tags=["Dealers - Inventory"]),
    update=extend_schema(tags=["Dealers - Inventory"]),
    partial_update=extend_schema(tags=["Dealers - Inventory"]),
    destroy=extend_schema(tags=["Dealers - Inventory"]),
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
        if self.action in ["create", "update", "partial_update", "destroy"]:
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
        description="Filter verified cars by fuel type and price range.",
        parameters=[
            OpenApiParameter("fuel_type", OpenApiTypes.STR, OpenApiParameter.QUERY,
                             description="Fuel type (electric, hybrid, petrol, diesel)"),
            OpenApiParameter("price_min", OpenApiTypes.FLOAT, OpenApiParameter.QUERY, description="Minimum price"),
            OpenApiParameter("price_max", OpenApiTypes.FLOAT, OpenApiParameter.QUERY, description="Maximum price"),
        ],
        responses=CarSerializer(many=True),
    )
    @action(detail=False, methods=['get'], serializer_class=CarSerializer)
    def filter(self, request):
        queryset = self.get_queryset()
        fuel_type = request.query_params.get('fuel_type')
        price_min = request.query_params.get('price_min')
        price_max = request.query_params.get('price_max')

        if fuel_type:
            queryset = queryset.filter(fuel_type=fuel_type)
        try:
            if price_min:
                queryset = queryset.filter(price__gte=float(price_min))
            if price_max:
                queryset = queryset.filter(price__lte=float(price_max))
        except ValueError:
            return Response({"error": "Price parameters must be valid numbers."}, status=400)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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
