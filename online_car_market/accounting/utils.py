from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from .models import Expense, FinancialReport
from online_car_market.sales.models import Sale


def generate_financial_report(dealer, report_type="profit_loss", month=None, year=None, conversion_rate=None):
    """
    Generate a financial report (profit/loss or balance sheet) for a dealer.

    Args:
        dealer: DealerProfile instance.
        report_type: 'profit_loss' or 'balance_sheet'.
        month/year: Optional filters for monthly or yearly reports.
        conversion_rate: Optional USD→ETB rate for currency conversion.
    """

    if not dealer:
        raise ValueError("Dealer must be provided.")

    # Defaults for current month/year if not provided
    today = timezone.now()
    month = month or today.month
    year = year or today.year

    # Prepare currency conversion rate
    conversion_rate = Decimal(conversion_rate) if conversion_rate else Decimal('57.00')  # Example default ETB/USD rate

    # Filter expenses by dealer and date
    expenses_qs = Expense.objects.filter(dealer=dealer, date__month=month, date__year=year)

    # If expenses are in USD, convert to ETB
    total_expenses_usd = expenses_qs.filter(currency='USD').aggregate(total=Sum('amount'))['total'] or Decimal(0)
    total_expenses_birr = expenses_qs.filter(currency='ETB').aggregate(total=Sum('amount'))['total'] or Decimal(0)

    total_expenses = total_expenses_birr + (total_expenses_usd * conversion_rate)

    # --- Handle Revenues ---
    # If you have a Sale model (each car sold), aggregate revenue:
    total_revenue_usd = \
    Sale.objects.filter(dealer=dealer, created_at__month=month, created_at__year=year, currency='USD').aggregate(
        total=Sum('price'))['total'] or Decimal(0)
    total_revenue_birr = \
    Sale.objects.filter(dealer=dealer, created_at__month=month, created_at__year=year, currency='ETB').aggregate(
        total=Sum('price'))['total'] or Decimal(0)

    total_revenue = total_revenue_birr + (total_revenue_usd * conversion_rate)

    # If report type is Profit/Loss
    if report_type == "profit_loss":
        net_profit = total_revenue - total_expenses

        data = {
            "month": month,
            "year": year,
            "currency": "ETB",
            "total_revenue_etb": float(total_revenue),
            "total_expenses_etb": float(total_expenses),
            "net_profit_etb": float(net_profit),
            "conversion_rate": float(conversion_rate)
        }

    # Balance Sheet type
    elif report_type == "balance_sheet":
        assets = total_revenue  # Simplified: all sales revenue
        liabilities = total_expenses
        equity = assets - liabilities

        data = {
            "month": month,
            "year": year,
            "currency": "ETB",
            "assets_etb": float(assets),
            "liabilities_etb": float(liabilities),
            "equity_etb": float(equity),
            "conversion_rate": float(conversion_rate)
        }

    else:
        raise ValueError("Invalid report type. Must be 'profit_loss' or 'balance_sheet'.")

    # Save or update report
    report, created = FinancialReport.objects.update_or_create(
        dealer=dealer,
        type=report_type,
        defaults={"data": data}
    )

    return report
