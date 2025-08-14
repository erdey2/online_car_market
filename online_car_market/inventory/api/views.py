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
from ..permissions import IsSuperAdminOrAdminOrDealer, IsSuperAdmin, IsAdmin, IsSuperAdminOrAdmin

@extend_schema_view(
    list=extend_schema(tags=["inventory"]),
    retrieve=extend_schema(tags=["inventory"]),
    create=extend_schema(tags=["inventory"]),
    update=extend_schema(tags=["inventory"]),
    partial_update=extend_schema(tags=["inventory"]),
    destroy=extend_schema(tags=["inventory"]),
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
        """
        Create a Car with optional uploaded images.
        Use multipart/form-data for uploaded_images as nested objects:
          uploaded_images[0].image_file
          uploaded_images[0].caption
          uploaded_images[0].is_featured
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        car = serializer.save()
        return Response(self.get_serializer(car).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='upload-images')
    def upload_images(self, request, pk=None):
        """
        Upload additional images to an existing car.
        Accept multipart/form-data with repeated field name `images`.
        """
        car = self.get_object()
        files = request.FILES.getlist('images')
        if not files:
            return Response(
                {"detail": "No files provided. Use form field name 'images'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        created = []
        for f in files:
            serializer = CarImageSerializer(
                data={'car': car.pk, 'image_file': f},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            created.append(serializer.data)

        return Response(created, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'], serializer_class=VerifyCarSerializer)
    @extend_schema(
        tags=["inventory"],
        description="Verify a car listing (admin/super_admin only).",
        responses=VerifyCarSerializer
    )
    def verify(self, request, pk=None):
        car = self.get_object()
        serializer = self.get_serializer(car, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    @extend_schema(
        tags=["inventory"],
        parameters=[
            OpenApiParameter(
                name='fuel_type', type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Fuel type of the car (electric, hybrid, petrol, diesel)'
            ),
            OpenApiParameter(
                name='price_min', type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY, description='Minimum price'
            ),
            OpenApiParameter(
                name='price_max', type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY, description='Maximum price'
            ),
        ],
        description="Filter verified cars by fuel type and price range.",
        responses=CarSerializer(many=True)
    )
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

@extend_schema_view(
    list=extend_schema(tags=["inventory"], description="List all car images."),
    retrieve=extend_schema(tags=["inventory"], description="Retrieve a specific car image."),
    create=extend_schema(tags=["inventory"], description="Create a car image (dealers/admins only)."),
    update=extend_schema(tags=["inventory"], description="Update a car image (dealers/admins only)."),
    partial_update=extend_schema(tags=["inventory"], description="Partially update a car image (dealers/admins only)."),
    destroy=extend_schema(tags=["inventory"], description="Delete a car image (dealers/admins only)."),
)
class CarImageViewSet(ModelViewSet):
    queryset = CarImage.objects.all()
    serializer_class = CarImageSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSuperAdminOrAdminOrDealer()]
        return [IsAuthenticated()]


