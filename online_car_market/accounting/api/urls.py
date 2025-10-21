from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExpenseViewSet, FinancialReportViewSet

router = DefaultRouter()
router.register(r'expenses', ExpenseViewSet)
router.register(r'financial-reports', FinancialReportViewSet, basename='financialreport')

urlpatterns = [
    path('', include(router.urls)),
]
