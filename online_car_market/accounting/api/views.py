from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from ..models import Expense, FinancialReport
from .serializers import ExpenseSerializer, FinancialReportSerializer
from online_car_market.users.api.views import IsAccounting
from drf_spectacular.utils import extend_schema, extend_schema_view

@extend_schema_view(
    list=extend_schema(tags=["accounting"]),
    retrieve=extend_schema(tags=["accounting"]),
    create=extend_schema(tags=["accounting"]),
    update=extend_schema(tags=["accounting"]),
    destroy=extend_schema(tags=["accounting"]),
)
class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsAccounting]

@extend_schema_view(
    list=extend_schema(tags=["accounting"]),
    retrieve=extend_schema(tags=["accounting"]),
    create=extend_schema(tags=["accounting"]),
    update=extend_schema(tags=["accounting"]),
    destroy=extend_schema(tags=["accounting"]),
)
class FinancialReportViewSet(ModelViewSet):
    queryset = FinancialReport.objects.all()
    serializer_class = FinancialReportSerializer
    permission_classes = [IsAuthenticated, IsAccounting]

