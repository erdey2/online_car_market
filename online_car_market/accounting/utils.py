from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from django.utils.timezone import now
from django.db import transaction


def generate_invoice_number(model, prefix="INV"):
    year = now().year

    with transaction.atomic():
        count = (
            model.objects
            .select_for_update()
            .filter(created_at__year=year)
            .count()
        ) + 1

    return f"{prefix}-{year}-{count:05d}"


def generate_financial_report(dealer, report_type="profit_loss", month=None, year=None):
    if not dealer:
        raise ValueError("Dealer must be provided.")

    from .models import Expense, Revenue, FinancialReport

    today = timezone.now()
    month = month or today.month
    year = year or today.year

    total_expenses = (
        Expense.objects
        .filter(company=dealer, created_at__month=month, created_at__year=year)
        .aggregate(total=Sum('converted_amount'))['total']
        or Decimal(0)
    )

    total_revenue = (
        Revenue.objects
        .filter(dealer=dealer, created_at__month=month, created_at__year=year)
        .aggregate(total=Sum('converted_amount'))['total']
        or Decimal(0)
    )

    if report_type == "profit_loss":
        data = {
            "month": month,
            "year": year,
            "currency": "ETB",
            "total_revenue_etb": float(total_revenue),
            "total_expenses_etb": float(total_expenses),
            "net_profit_etb": float(total_revenue - total_expenses),
        }

    elif report_type == "balance_sheet":
        data = {
            "month": month,
            "year": year,
            "currency": "ETB",
            "assets_etb": float(total_revenue),
            "liabilities_etb": float(total_expenses),
            "equity_etb": float(total_revenue - total_expenses),
        }

    else:
        raise ValueError("Invalid report type.")

    report, _ = FinancialReport.objects.update_or_create(
        dealer=dealer,
        type=report_type,
        defaults={"data": data}
    )

    return report
