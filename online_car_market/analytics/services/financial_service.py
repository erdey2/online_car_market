from django.db.models import Sum, F, Avg, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from online_car_market.accounting.models import Expense, CarExpense, Revenue

class FinancialAnalyticsService:
    TRUNC_MAP = {
        "day": TruncDay,
        "week": TruncWeek,
        "month": TruncMonth,
        "year": TruncYear,
    }

    @classmethod
    def get_financial_analytics(cls, dealer, period="month"):
        Trunc = cls.TRUNC_MAP.get(period, TruncMonth)

        # EXPENSES
        general_expenses = (
            Expense.objects.filter(company=dealer)
            .annotate(period=Trunc("created_at"))
            .annotate(final_amount=F("amount") * F("exchange_rate"))
            .values("period")
            .annotate(total=Sum("final_amount"))
            .order_by("period")
        )

        car_expenses = (
            CarExpense.objects.filter(company=dealer)
            .annotate(period=Trunc("created_at"))
            .values("period")
            .annotate(total=Sum("converted_amount"))
            .order_by("period")
        )

        # Merge expenses by period
        expense_map = {}
        for row in general_expenses:
            expense_map[row["period"]] = row["total"]
        for row in car_expenses:
            expense_map[row["period"]] = expense_map.get(row["period"], 0) + row["total"]

        # REVENUE
        revenue_qs = (
            Revenue.objects.filter(dealer=dealer)
            .annotate(period=Trunc("created_at"))
            .values("period")
            .annotate(total=Sum("converted_amount"))
            .order_by("period")
        )
        revenue_map = {r["period"]: r["total"] for r in revenue_qs}

        # Combine into analytics rows
        periods = sorted(set(list(expense_map.keys()) + list(revenue_map.keys())))
        results = []
        total_expenses = total_revenue = 0
        for p in periods:
            exp = expense_map.get(p, 0)
            rev = revenue_map.get(p, 0)
            total_expenses += exp
            total_revenue += rev
            results.append({
                "period": p.date().strftime("%Y-%m-%d"),
                "expense": round(exp, 2),
                "revenue": round(rev, 2),
                "net_profit": round(rev - exp, 2)
            })

        return {
            "range": period,
            "total_expenses": round(total_expenses, 2),
            "total_revenue": round(total_revenue, 2),
            "net_profit": round(total_revenue - total_expenses, 2),
            "results": results
        }
