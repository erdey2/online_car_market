def calculate_income_tax(taxable_income: float) -> float:
    """
    Calculate Ethiopian income tax based on monthly taxable income.

    Tax brackets (monthly):
    <= 600        : 0%
    601 – 1650    : 10%  - 60
    1651 – 3200   : 15%  - 142.5
    3201 – 5250   : 20%  - 302.5
    5251 – 7800   : 25%  - 565
    7801 – 10900  : 30%  - 955
    > 10900       : 35%  - 1500
    """

    if taxable_income <= 600:
        tax = 0
    elif taxable_income <= 1650:
        tax = taxable_income * 0.10 - 60
    elif taxable_income <= 3200:
        tax = taxable_income * 0.15 - 142.5
    elif taxable_income <= 5250:
        tax = taxable_income * 0.20 - 302.5
    elif taxable_income <= 7800:
        tax = taxable_income * 0.25 - 565
    elif taxable_income <= 10900:
        tax = taxable_income * 0.30 - 955
    else:
        tax = taxable_income * 0.35 - 1500

    # Tax should never be negative
    return round(max(tax, 0), 2)

