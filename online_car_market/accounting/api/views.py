from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rolepermissions.checkers import has_role
from ..models import Expense, FinancialReport
from .serializers import ExpenseSerializer, FinancialReportSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view

class CanManageAccounting(BasePermission):
    """Only super_admin, admin, broker, or dealer can manage sales."""
    def has_permission(self, request, view):
        return has_role(request.user, ['super_admin', 'admin', 'broker', 'dealer', 'accountant'])

# -----------------------
# Expense ViewSet
# -----------------------
@extend_schema_view(
    list=extend_schema(tags=["Dealers - Accounting"]),
    retrieve=extend_schema(tags=["Dealers - Accounting"]),
    create=extend_schema(tags=["Dealers - Accounting"]),
    update=extend_schema(tags=["Dealers - Accounting"]),
    partial_update=extend_schema(tags=["Dealers - Accounting"]),
    destroy=extend_schema(tags=["Dealers - Accounting"]),
)
class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageAccounting()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, 'dealer'):
            return Expense.objects.filter(dealer=user)
        if has_role(user, ['super_admin', 'admin', 'accounting']):
            return Expense.objects.all()
        return Expense.objects.none()

# -----------------------
# FinancialReport ViewSet
# -----------------------
@extend_schema_view(
    list=extend_schema(tags=["Dealers - Accounting"]),
    retrieve=extend_schema(tags=["Dealers - Accounting"]),
    create=extend_schema(tags=["Dealers - Accounting"]),
    update=extend_schema(tags=["Dealers - Accounting"]),
    partial_update=extend_schema(tags=["Dealers - Accounting"]),
    destroy=extend_schema(tags=["Dealers - Accounting"]),
)
class FinancialReportViewSet(ModelViewSet):
    queryset = FinancialReport.objects.all()
    serializer_class = FinancialReportSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageAccounting()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, 'dealer'):
            return FinancialReport.objects.filter(dealer=user)
        if has_role(user, ['super_admin', 'admin', 'accounting']):
            return FinancialReport.objects.all()
        return FinancialReport.objects.none()
