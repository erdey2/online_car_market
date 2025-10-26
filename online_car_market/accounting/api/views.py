from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rolepermissions.checkers import has_role
from ..models import Expense, FinancialReport, DealerProfile, CarExpense, Revenue, ExchangeRate
from .serializers import ExpenseSerializer, FinancialReportSerializer, CarExpenseSerializer, RevenueSerializer, ExchangeRateSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from online_car_market.accounting.utils import generate_financial_report


class CanManageAccounting(BasePermission):
    """Only super_admin, admin, broker, dealer, or accountant can manage accounting data."""
    def has_permission(self, request, view):
        return has_role(request.user, ['super_admin', 'admin', 'broker', 'dealer', 'accountant'])

@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Accounting"],
        summary="List all exchange rates",
        description="Retrieve a list of all exchange rates ordered by date (most recent first)."
    ),
    retrieve=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Retrieve a specific exchange rate",
        description="Get detailed information about a specific exchange rate record."
    ),
    create=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Add a new exchange rate",
        description="Allows an authorized accountant, admin, or dealer to record a new USD/ETB rate."
    ),
    update=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Update an exchange rate",
        description="Modify existing exchange rate details."
    ),
    partial_update=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Partially update an exchange rate",
        description="Partially update fields in an existing exchange rate record."
    ),
    destroy=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Delete an exchange rate",
        description="Remove an exchange rate record (admin-only action)."
    ),
)
class ExchangeRateViewSet(ModelViewSet):
    """Manage daily USD/ETB exchange rates for accurate financial conversions."""
    queryset = ExchangeRate.objects.all().order_by('-date')
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated, CanManageAccounting]

# ------------------------------------
@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Accounting"],
        summary="List car-specific expenses",
        description="Retrieve all expenses related to cars (e.g., shipping, customs, transport)."
    ),
    retrieve=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Retrieve a car expense",
        description="Get detailed expense information for a specific car."
    ),
    create=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Record a new car expense",
        description="Add a new expense related to a car — in ETB or USD. Supports currency conversion."
    ),
    update=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Update a car expense record",
        description="Modify an existing car expense."
    ),
    partial_update=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Partially update a car expense record",
        description="Update specific fields of an existing car expense."
    ),
    destroy=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Delete a car expense record",
        description="Remove a car expense entry (admin or accountant only)."
    ),
)
class CarExpenseViewSet(ModelViewSet):
    """Handle car-related expenses including transport, tax, shipping, and maintenance."""
    queryset = CarExpense.objects.all()
    serializer_class = CarExpenseSerializer
    permission_classes = [IsAuthenticated, CanManageAccounting]

# ------------------------------------
@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Accounting"],
        summary="List all revenue entries",
        description="View all recorded revenues from car sales and broker payments."
    ),
    retrieve=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Retrieve a specific revenue record",
        description="Get detailed information for a single revenue transaction."
    ),
    create=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Record a new revenue",
        description="Add new revenue entries (e.g., from car sale or broker payment)."
    ),
    update=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Update a revenue entry",
        description="Edit an existing revenue record."
    ),
    partial_update=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Partially update a revenue entry",
        description="Partially update revenue details (amount, currency, date, etc.)."
    ),
    destroy=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Delete a revenue record",
        description="Remove a revenue entry (admin or accountant only)."
    ),
)
class RevenueViewSet(ModelViewSet):
    """Manage all sources of income including sales and broker fees."""
    queryset = Revenue.objects.all()
    serializer_class = RevenueSerializer
    permission_classes = [IsAuthenticated, CanManageAccounting]

# Expense ViewSet
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
            dealer_profile = DealerProfile.objects.filter(profile__user=user).first()
            return Expense.objects.filter(dealer=dealer_profile) if dealer_profile else Expense.objects.none()
        if has_role(user, ['super_admin', 'admin', 'accountant', 'dealer']):
            return Expense.objects.all()
        return Expense.objects.none()

# FinancialReport ViewSet
@extend_schema_view(
    list=extend_schema(tags=["Dealers - Accounting"]),
    retrieve=extend_schema(tags=["Dealers - Accounting"]),
    generate_report=extend_schema(tags=["Dealers - Accounting"]),
)
class FinancialReportViewSet(ModelViewSet):
    queryset = FinancialReport.objects.all()
    serializer_class = FinancialReportSerializer
    http_method_names = ['get', 'post']  # Disable create/update/delete except generate_report

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['dealer']):
            return FinancialReport.objects.filter(dealer__profile__user=user)
        return FinancialReport.objects.all()

    @extend_schema(
        description="Automatically generate a financial report (profit_loss or balance_sheet) for a dealer.",
        parameters=[
            OpenApiParameter(
                name="type",
                type=str,
                enum=["profit_loss", "balance_sheet"],
                required=True,
                description="Type of report to generate"
            )
        ],
        responses={
            200: FinancialReportSerializer,
            400: OpenApiResponse(description="Invalid input or permission denied"),
        },
        tags=["Dealers - Accounting"],
    )
    @action(detail=False, methods=['post'], url_path='generate')
    def generate_report(self, request):
        """Generate a new report for the dealer."""
        user = request.user
        report_type = request.data.get('type', 'profit_loss')
        month = request.data.get('month')
        year = request.data.get('year')

        if not has_role(user, ['super_admin', 'admin', 'dealer', 'accountant']):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        dealer = DealerProfile.objects.filter(profile__user=user).first()
        if not dealer:
            return Response(
                {"detail": "Dealer profile not found or not linked correctly."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            report = generate_financial_report(dealer, report_type, month, year)
            serializer = self.get_serializer(report)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

