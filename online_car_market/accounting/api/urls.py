from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExpenseViewSet, FinancialReportViewSet, CarExpenseViewSet, RevenueViewSet, ExchangeRateViewSet, ExpenseFilter

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet)
router.register('car-expenses', CarExpenseViewSet)
router.register('revenues', RevenueViewSet)
router.register('exchange-rates', ExchangeRateViewSet)
router.register(r'financial-reports', FinancialReportViewSet, basename='financialreport')

urlpatterns = [
    path('', include(router.urls)),
]
