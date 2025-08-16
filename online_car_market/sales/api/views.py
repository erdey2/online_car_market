from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rolepermissions.permissions import register_object_checker
from rolepermissions.checkers import has_role
from ..models import Sale, Lead
from .serializers import SaleSerializer, LeadSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view

# Object-level permission
@register_object_checker()
def has_manage_sales_permission(permission, user, obj):
    return has_role(user, ['super_admin', 'admin', 'sales', 'dealer'])

# Sale ViewSet
@extend_schema_view(
    list=extend_schema(tags=["Dealers - Sales"]),
    retrieve=extend_schema(tags=["Dealers - Sales"]),
    create=extend_schema(tags=["Dealers - Sales"]),
    update=extend_schema(tags=["Dealers - Sales"]),
    partial_update=extend_schema(tags=["Dealers - Sales"]),
    destroy=extend_schema(tags=["Dealers - Sales"]),
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
        # Dealer sees only their sales
        if has_role(user, 'dealer'):
            return Sale.objects.filter(dealer__user=user)
        # Sales users see their assigned sales
        if has_role(user, 'sales'):
            return Sale.objects.filter(sales_user=user)
        # Admins/super_admins see all
        if has_role(user, ['super_admin', 'admin']):
            return Sale.objects.all()
        return Sale.objects.none()

# Lead ViewSet
@extend_schema_view(
    list=extend_schema(tags=["Dealers - Sales"]),
    retrieve=extend_schema(tags=["Dealers - Sales"]),
    create=extend_schema(tags=["Dealers - Sales"]),
    update=extend_schema(tags=["Dealers - Sales"]),
    partial_update=extend_schema(tags=["Dealers - Sales"]),
    destroy=extend_schema(tags=["Dealers - Sales"]),
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
        if has_role(user, 'dealer'):
            return Lead.objects.filter(dealer=user)
        if has_role(user, 'sales'):
            return Lead.objects.filter(assigned_sales=user)
        if has_role(user, ['super_admin', 'admin']):
            return Lead.objects.all()
        return Lead.objects.none()
