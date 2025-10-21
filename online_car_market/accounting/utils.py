from decimal import Decimal
from django.db.models import Sum
from .models import Expense, FinancialReport

def generate_financial_report(dealer, report_type="profit_loss"):
    """
    Generate a financial report (profit/loss or balance sheet) for a dealer.
    """
    if not dealer:
        raise ValueError("Dealer must be provided.")

    if report_type == "profit_loss":
        # Sum expenses by type
        total_expenses = Expense.objects.filter(dealer=dealer).aggregate(
            total=Sum('amount')
        )['total'] or Decimal(0)

        # For simplicity, assume total revenue is stored or fixed temporarily.
        # Later, you can calculate it from sales data.
        total_revenue = Decimal(100000)  # Replace this with your Sales model aggregation
        net_profit = total_revenue - total_expenses

        data = {
            "total_revenue": float(total_revenue),
            "total_expenses": float(total_expenses),
            "net_profit": float(net_profit)
        }

    elif report_type == "balance_sheet":
        # Simple placeholder example; you can expand this later
        assets = Decimal(200000)  # e.g., cars owned, cash on hand, etc.
        liabilities = Expense.objects.filter(dealer=dealer).aggregate(
            total=Sum('amount')
        )['total'] or Decimal(0)
        equity = assets - liabilities

        data = {
            "assets": float(assets),
            "liabilities": float(liabilities),
            "equity": float(equity)
        }

    else:
        raise ValueError("Invalid report type. Must be 'profit_loss' or 'balance_sheet'.")

    # Save or update the report
    report, created = FinancialReport.objects.update_or_create(
        dealer=dealer,
        type=report_type,
        defaults={"data": data}
    )

    return report
