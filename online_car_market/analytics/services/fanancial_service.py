from django.db.models import Sum, F
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from online_car_market.accounting.models import Expense, CarExpense, Revenue
from online_car_market.dealers.models import DealerProfile


class FinancialAnalyticsService:

    TRUNC_MAP = {
        "day": TruncDay,
        "week": TruncWeek,
        "month": TruncMonth,
        "year": TruncYear,
    }

    @classmethod
    def get_financial_analytics(cls, user, period="month"):
        dealer = DealerProfile.objects.get(profile=user.profile)

        Trunc = cls.TRUNC_MAP.get(period, TruncMonth)

        general_expenses = (
            Expense.objects.filter(dealer=dealer)
            .annotate(period=Trunc("created_at"))
            .annotate(final_amount=F("amount") * F("exchange_rate"))
            .values("period")
            .annotate(total=Sum("final_amount"))
        )

        revenue = (
            Revenue.objects.filter(dealer=dealer)
            .annotate(period=Trunc("created_at"))
            .values("period")
            .annotate(total=Sum("converted_amount"))
        )

        return {
            "expenses": list(general_expenses),
            "revenue": list(revenue),
        }
