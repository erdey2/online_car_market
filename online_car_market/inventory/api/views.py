from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rolepermissions.permissions import register_object_checker
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from ..models import Car, CarImage
from .serializers import CarSerializer, CarImageSerializer


@register_object_checker()
def has_manage_inventory_permission(permission, user, obj):
    return has_role(user, ['super_admin', 'admin', 'dealer'])

@extend_schema_view(
    list=extend_schema(tags=["inventory"]),
    retrieve=extend_schema(tags=["inventory"]),
    create=extend_schema(tags=["inventory"]),
    update=extend_schema(tags=["inventory"]),
    partial_update=extend_schema(tags=["inventory"]),
    destroy=extend_schema(tags=["inventory"]),
)
class CarViewSet(ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_inventory_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, 'dealer'):
            return Car.objects.filter(dealer__user=user)
        if has_role(user, ['super_admin', 'admin']):
            return Car.objects.all()
        return Car.objects.filter(status='available')

    @extend_schema(
        parameters=[
            OpenApiParameter(name='fuel_type', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, description='Fuel type of the car (electric, hybrid, petrol, diesel)'),
            OpenApiParameter(name='price_min', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Minimum price'),
            OpenApiParameter(name='price_max', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY, description='Maximum price'),
        ],
        description="Filter cars by fuel type and price range.",
        responses=CarSerializer(many=True)
    )
    @action(detail=False, methods=['get'])
    def filter(self, request):
        queryset = self.get_queryset()
        fuel_type = request.query_params.get('fuel_type')
        price_min = request.query_params.get('price_min')
        price_max = request.query_params.get('price_max')

        if fuel_type and fuel_type not in ['electric', 'hybrid', 'petrol', 'diesel']:
            return Response({"error": "Invalid fuel type. Must be one of: electric, hybrid, petrol, diesel."}, status=400)
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
    list=extend_schema(tags=["inventory"]),
    retrieve=extend_schema(tags=["inventory"]),
    create=extend_schema(tags=["inventory"]),
    update=extend_schema(tags=["inventory"]),
    partial_update=extend_schema(tags=["inventory"]),
    destroy=extend_schema(tags=["inventory"]),
)
class CarImageViewSet(ModelViewSet):
    queryset = CarImage.objects.all()
    serializer_class = CarImageSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_inventory_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, 'dealer'):
            return CarImage.objects.filter(car__dealer__user=user)
        if has_role(user, ['super_admin', 'admin']):
            return CarImage.objects.all()
        return CarImage.objects.filter(car__status='available')
