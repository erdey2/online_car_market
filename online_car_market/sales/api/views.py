from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from ..models import Sale, Lead
from .serializers import SaleSerializer, LeadSerializer
from online_car_market.users.api.views import IsSales, IsAccounting
from drf_spectacular.utils import extend_schema, extend_schema_view

@extend_schema_view(
    list=extend_schema(tags=["sales"]),
    retrieve=extend_schema(tags=["sales"]),
    create=extend_schema(tags=["sales"]),
    update=extend_schema(tags=["sales"]),
    destroy=extend_schema(tags=["sales"]),
)
class SaleViewSet(ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAuthenticated(), IsSales()]
        return [IsAuthenticated(), IsAccounting()]

@extend_schema_view(
    list=extend_schema(tags=["sales"]),
    retrieve=extend_schema(tags=["sales"]),
    create=extend_schema(tags=["sales"]),
    update=extend_schema(tags=["sales"]),
    destroy=extend_schema(tags=["sales"]),
)
class LeadViewSet(ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated, IsSales]
