from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from ..models import Sale, Lead
from .serializers import SaleSerializer, LeadSerializer
from online_car_market.users.api.views import IsSales, IsAccounting

class SaleViewSet(ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAuthenticated(), IsSales()]
        return [IsAuthenticated(), IsAccounting()]

class LeadViewSet(ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated, IsSales]
