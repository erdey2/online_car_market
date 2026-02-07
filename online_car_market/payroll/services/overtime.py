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

    if total_hours_worked <= 0:
        raise ValueError("Total hours worked must be greater than zero")

    try:
        multiplier = OVERTIME_RATES[overtime_type]
    except KeyError:
        raise ValueError(f"Invalid overtime type: {overtime_type}")

    hourly_rate = (basic_salary / total_hours_worked).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    overtime_amount = hourly_rate * multiplier * overtime_hours

    return overtime_amount.quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
