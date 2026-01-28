from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal("0.00")


def calculate_income_tax(taxable_income: Decimal) -> Decimal:
    """
    Ethiopian monthly income tax
    """

    taxable_income = Decimal(taxable_income)

    if taxable_income <= 600:
        tax = ZERO
    elif taxable_income <= 1650:
        tax = taxable_income * Decimal("0.10") - Decimal("60")
    elif taxable_income <= 3200:
        tax = taxable_income * Decimal("0.15") - Decimal("142.50")
    elif taxable_income <= 5250:
        tax = taxable_income * Decimal("0.20") - Decimal("302.50")
    elif taxable_income <= 7800:
        tax = taxable_income * Decimal("0.25") - Decimal("565")
    elif taxable_income <= 10900:
        tax = taxable_income * Decimal("0.30") - Decimal("955")
    else:
        tax = taxable_income * Decimal("0.35") - Decimal("1500")

    if tax < ZERO:
        tax = ZERO

    return tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
