import django_filters
from django.db.models import Sum
from django_filters.rest_framework.backends import DjangoFilterBackend

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from rolepermissions.checkers import has_role
from ..models import Expense, FinancialReport, DealerProfile, CarExpense, Revenue, ExchangeRate
from .serializers import ExpenseSerializer, FinancialReportSerializer, CarExpenseSerializer, RevenueSerializer, ExchangeRateSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from online_car_market.accounting.utils import generate_financial_report
from online_car_market.dealers.models import DealerStaff
from online_car_market.users.permissions.business_permissions import CanManageAccounting


# Exchange rate
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

# car expense
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

    @extend_schema(
        tags=["Dealers - Accounting"],
        summary="Get total expenses per car per dealer",
        description=(
            "Returns aggregated car expenses grouped by dealer and car. "
            "Includes total converted amount (ETB) and detailed expense breakdown per car."
        ),
        responses={
            200: OpenApiResponse(
                description="List of dealers with their cars and total expenses in ETB."
            )
        },
    )
    @action(detail=False, methods=["get"], url_path="per-dealer-car")
    def expenses_per_dealer_car(self, request):
        """Aggregate total expenses per car per dealer."""
        dealers = (
            CarExpense.objects.values("dealer_id", "dealer__company_name").distinct()
        )

        results = []
        for dealer in dealers:
            dealer_id = dealer["dealer_id"]
            dealer_name = dealer["dealer__company_name"]

            # Cars under this dealer
            cars = (
                CarExpense.objects.filter(dealer_id=dealer_id)
                .values("car_id", "car__model")
                .annotate(total_expenses_etb=Sum("converted_amount"))
                .order_by("-total_expenses_etb")
            )

            car_data = []
            for car in cars:
                car_expenses = CarExpense.objects.filter(
                    dealer_id=dealer_id, car_id=car["car_id"]
                )
                expense_list = [
                    {
                        "description": e.description,
                        "amount": float(e.amount),
                        "currency": e.currency,
                        "converted_amount": float(e.converted_amount or 0),
                        "date": e.date,
                    }
                    for e in car_expenses
                ]

                car_data.append({
                    "car_id": car["car_id"],
                    "car_model": car["car__model"],
                    "total_expenses_etb": float(car["total_expenses_etb"] or 0),
                    "expenses": expense_list,
                })

            results.append({
                "dealer_id": dealer_id,
                "dealer": dealer_name,
                "cars": car_data,
            })

        return Response(results)

# revenue
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

class ExpenseFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    end_date = django_filters.DateFilter(field_name="date", lookup_expr="lte")
    dealer = django_filters.NumberFilter(field_name="dealer__id")
    currency = django_filters.CharFilter(field_name="currency")

    class Meta:
        model = Expense
        fields = ['dealer', 'currency', 'start_date', 'end_date']

# Expense ViewSet
@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Accounting"],
        summary="List all general expenses",
        description="Retrieve all recorded expenses (e.g., operational, administrative, or miscellaneous dealer expenses). "
                    "Admins, accountants, and dealers can view their respective expenses."
    ),
    retrieve=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Retrieve a specific expense record",
        description="Fetch detailed information about a single expense, including amount, currency, dealer, and description."
    ),
    create=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Record a new expense",
        description="Create a new expense entry for a dealer. "
                    "Supports both ETB and USD currencies, and only accountants or dealers can create records."
    ),
    update=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Update an expense record",
        description="Modify an existing expense entry — allowed for accountants, dealers, and admins."
    ),
    partial_update=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Partially update an expense record",
        description="Update specific fields of an expense record (e.g., amount or currency). "
                    "Only accessible to users with accounting permissions."
    ),
    destroy=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Delete an expense record",
        description="Remove an existing expense entry. "
                    "Only admins or accountants can perform deletions."
    ),
)
class ExpenseViewSet(ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    queryset = Expense.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = ExpenseFilter

    def get_permissions(self):
        # Special write permissions
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageAccounting()]
        # Default read permissions
        return [permission() for permission in self.permission_classes]

    def get_queryset(self):
        user = self.request.user

        base_qs = Expense.objects.select_related("company")

        # Dealers can only see their own expenses
        if has_role(user, 'dealer'):
            dealer_profile = DealerProfile.objects.filter(profile__user=user).first()
            return base_qs.filter(company=dealer_profile) if dealer_profile else base_qs.none()

        # Admin-level roles can see everything
        if has_role(user, ['super_admin', 'admin', 'accountant']):
            return base_qs

        # Others see nothing
        return base_qs.none()

    def perform_create(self, serializer):
        """Restrict dealer so they can only create THEIR OWN expense"""
        user = self.request.user
        if has_role(user, 'dealer'):
            dealer_profile = DealerProfile.objects.filter(profile__user=user).first()
            serializer.save(company=dealer_profile)
        else:
            serializer.save()

# FinancialReport ViewSet
@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Accounting"],
        summary="List all generated financial reports",
        description=(
            "Retrieve a list of all generated financial reports, including profit/loss statements "
            "and balance sheets. Dealers can view their own reports, while admins and accountants "
            "can access all dealer reports."
        ),
    ),
    retrieve=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Retrieve a specific financial report",
        description=(
            "Get detailed information about a single financial report, including report type, "
            "period (month/year), total revenue, total expenses, and calculated profit or loss."
        ),
    ),
    generate_report=extend_schema(
        tags=["Dealers - Accounting"],
        summary="Generate a new financial report",
        description=(
            "Automatically generate a financial report for a specific dealer. Supports two types: "
            "`profit_loss` and `balance_sheet`. This endpoint calculates the totals based on recorded "
            "revenues, car expenses, and general expenses for the selected month and year."
        ),
    ),
)
class FinancialReportViewSet(ModelViewSet):
    """
    ViewSet for managing and generating financial reports for dealers.
    Allows accountants, admins, and dealers to view or generate reports that
    summarize revenues, expenses, and profit/loss statements.
    """
    queryset = FinancialReport.objects.all()
    serializer_class = FinancialReportSerializer
    http_method_names = ['get', 'post']  # Disable create/update/delete except generate_report

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['dealer']):
            return FinancialReport.objects.filter(dealer__profile__user=user)
        return FinancialReport.objects.all()

    @extend_schema(
        summary="Generate a dealer financial report",
        description=(
            "Creates a financial report for the authenticated dealer or specified period. "
            "Includes automatic calculation of total revenue, total expenses, and net profit/loss. "
            "Accessible by dealers, accountants, admins, and super admins only."
        ),
        parameters=[
            OpenApiParameter(
                name="type",
                type=str,
                enum=["profit_loss", "balance_sheet"],
                required=True,
                description="Type of report to generate (profit_loss or balance_sheet)."
            ),
            OpenApiParameter(
                name="month",
                type=int,
                required=False,
                description="Month (1-12) for which to generate the report. Optional — defaults to current month."
            ),
            OpenApiParameter(
                name="year",
                type=int,
                required=False,
                description="Year (e.g., 2025) for which to generate the report. Optional — defaults to current year."
            ),
        ],
        responses={
            200: FinancialReportSerializer,
            400: OpenApiResponse(description="Invalid input or permission denied"),
        },
        tags=["Dealers - Accounting"],
    )
    @action(detail=False, methods=['post'], url_path='generate')
    def generate_report(self, request):
        user = request.user
        report_type = request.data.get('type', 'profit_loss')
        month = request.data.get('month')
        year = request.data.get('year')

        if not has_role(user, ['super_admin', 'admin', 'dealer', 'accountant']):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        dealer = None

        if has_role(user, "dealer"):
            dealer = DealerProfile.objects.filter(profile__user=user).first()

        elif has_role(user, "accountant"):
            dealer_id = (
                DealerStaff.objects
                .filter(user=user)
                .values_list("dealer_id", flat=True)
                .first()
            )
            if dealer_id:
                dealer = DealerProfile.objects.filter(id=dealer_id).first()

        elif has_role(user, ["admin", "super_admin"]):
            dealer_id = request.data.get("dealer_id")
            if dealer_id:
                dealer = DealerProfile.objects.filter(id=dealer_id).first()

        if not dealer:
            return Response(
                {
                    "detail": (
                        "Dealer could not be resolved. "
                        "Dealers use their own profile, "
                        "accountants must be linked to a dealer, "
                        "and admins must provide dealer_id."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            report = generate_financial_report(dealer, report_type, month, year)
            serializer = self.get_serializer(report)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)



