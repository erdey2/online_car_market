from decimal import Decimal

OVERTIME_RATES = {
    "1.5": Decimal("1.5"),
    "1.75": Decimal("1.75"),
    "2.0": Decimal("2.0"),
    "2.5": Decimal("2.5"),
}

def calculate_overtime(hourly_rate, hours_by_rate: dict):
    """
    hours_by_rate example:
    {
        "1.5": 4,
        "1.75": 3,
        "2.0": 1,
        "2.5": 2
    }
    """
    total_hours = Decimal("0")
    total_amount = Decimal("0")

    for rate, hours in hours_by_rate.items():
        multiplier = OVERTIME_RATES[rate]
        hours = Decimal(hours)

        total_hours += hours
        total_amount += hourly_rate * multiplier * hours

    return {
        "total_hours": total_hours,
        "total_amount": total_amount,
    }
