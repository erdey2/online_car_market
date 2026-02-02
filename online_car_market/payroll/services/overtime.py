from decimal import Decimal, ROUND_HALF_UP

OVERTIME_RATES = {
    "1.5": Decimal("1.5"),
    "1.75": Decimal("1.75"),
    "2.0": Decimal("2.0"),
    "2.5": Decimal("2.5"),
}


def calculate_overtime_amount(
    basic_salary: Decimal,
    total_hours_worked: Decimal,
    overtime_hours: Decimal,
    overtime_type: str,
) -> Decimal:
    """
    Ethiopian overtime calculation:
    Hourly rate = basic_salary / total_hours_worked
    Overtime pay = hourly_rate * multiplier * overtime_hours
    """

    hourly_rate = (basic_salary / total_hours_worked).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    multiplier = OVERTIME_RATES[overtime_type]

    overtime_amount = hourly_rate * multiplier * overtime_hours

    return overtime_amount.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

