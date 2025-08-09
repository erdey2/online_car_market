from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from ..models import Car, CarImage
from .serializers import CarSerializer, CarImageSerializer, VerifyCarSerializer
from ..permissions import IsSuperAdminOrAdminOrDealer, IsSuperAdmin, IsAdmin, IsSuperAdminOrAdmin

@extend_schema_view(
    list=extend_schema(tags=["inventory"], description="List all verified cars for non-admins or all cars for admins."),
    retrieve=extend_schema(tags=["inventory"], description="Retrieve a specific car if verified or user is admin."),
    create=extend_schema(tags=["inventory"], description="Create a car listing (dealers/admins only)."),
    update=extend_schema(tags=["inventory"], description="Update a car listing (dealers/admins only)."),
    partial_update=extend_schema(tags=["inventory"], description="Partially update a car listing (dealers/admins only)."),
    destroy=extend_schema(tags=["inventory"], description="Delete a car listing (dealers/admins only)."),
)
class CarViewSet(ModelViewSet):
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return Car.objects.all()
        return Car.objects.filter(verification_status='verified')

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSuperAdminOrAdminOrDealer()]
        elif self.action == 'verify':
            return [IsAuthenticated(), IsSuperAdminOrAdmin()]
        return [IsAuthenticated()]

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
            OpenApiParameter(name='fuel_type', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Fuel type of the car (electric, hybrid, petrol, diesel)'),
            OpenApiParameter(name='price_min', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Minimum price'),
            OpenApiParameter(name='price_max', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Maximum price'),
        ],
        description="Filter verified cars by fuel type and price range.",
        responses=CarSerializer(many=True)
    )
    def filter(self, request):
        queryset = self.get_queryset()
        fuel_type = request.query_params.get('fuel_type')
        price_min = request.query_params.get('price_min')
        price_max = request.query_params.get('price_max')

        valid_fuel_types = [choice[0] for choice in Car.FUEL_TYPES]
        if fuel_type and fuel_type not in valid_fuel_types:
            return Response({"error": f"Invalid fuel type. Must be one of: {', '.join(valid_fuel_types)}."}, status=400)

        if fuel_type:
            queryset = queryset.filter(fuel_type=fuel_type)

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
