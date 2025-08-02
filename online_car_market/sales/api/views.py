from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rolepermissions.permissions import register_object_checker
from rolepermissions.checkers import has_role
from ..models import Sale, Lead
from .serializers import SaleSerializer, LeadSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view

@register_object_checker()
def has_manage_sales_permission(permission, user, obj):
    return has_role(user, ['super_admin', 'admin', 'sales'])

@extend_schema_view(
    list=extend_schema(tags=["sales"]),
    retrieve=extend_schema(tags=["sales"]),
    create=extend_schema(tags=["sales"]),
    update=extend_schema(tags=["sales"]),
    partial_update=extend_schema(tags=["sales"]),
    destroy=extend_schema(tags=["sales"]),
)
class SaleViewSet(ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_sales_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, 'buyer'):
            return Sale.objects.filter(buyer__user=user)
        if has_role(user, 'broker'):
            return Sale.objects.filter(broker__user=user)
        if has_role(user, ['super_admin', 'admin', 'sales']):
            return Sale.objects.all()
        return Sale.objects.none()

@extend_schema_view(
    list=extend_schema(tags=["sales"]),
    retrieve=extend_schema(tags=["sales"]),
    create=extend_schema(tags=["sales"]),
    update=extend_schema(tags=["sales"]),
    partial_update=extend_schema(tags=["sales"]),
    destroy=extend_schema(tags=["sales"]),
)
class LeadViewSet(ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_sales_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, 'sales'):
            return Lead.objects.filter(assigned_sales=user)
        if has_role(user, ['super_admin', 'admin']):
            return Lead.objects.all()
        return Lead.objects.none()
