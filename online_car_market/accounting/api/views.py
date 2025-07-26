from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Expense, FinancialReport
from .serializers import ExpenseSerializer, FinancialReportSerializer
from online_car_market.users.api.views import IsAccounting

class ExpenseViewSet(ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated, IsAccounting]

class FinancialReportViewSet(ModelViewSet):
    queryset = FinancialReport.objects.all()
    serializer_class = FinancialReportSerializer
    permission_classes = [IsAuthenticated, IsAccounting]

