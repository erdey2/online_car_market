from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import Car
from .serializers import CarSerializer
from online_car_market.users.api.views import IsAdmin, IsSales
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes


@extend_schema_view(
    list=extend_schema(tags=["inventory"]),
    retrieve=extend_schema(tags=["inventory"]),
    create=extend_schema(tags=["inventory"]),
    update=extend_schema(tags=["inventory"]),
    destroy=extend_schema(tags=["inventory"]),
)
class CarViewSet(ModelViewSet):
    queryset = Car.objects.all()
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAuthenticated(), IsSales()]
        elif self.action == 'destroy':
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    @extend_schema(
        parameters=[
            OpenApiParameter(name='fuel_type', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY,
                             description='Fuel type of the car'),
            OpenApiParameter(name='price_min', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY,
                             description='Minimum price'),
            OpenApiParameter(name='price_max', type=OpenApiTypes.FLOAT, location=OpenApiParameter.QUERY,
                             description='Maximum price'),
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
      if fuel_type:
          queryset = queryset.filter(fuel_type=fuel_type)
      if price_min:
          queryset = queryset.filter(price__gte=price_min)
      if price_max:
          queryset = queryset.filter(price__lte=price_max)
      serializer = self.get_serializer(queryset, many=True)
      return Response(serializer.data)
