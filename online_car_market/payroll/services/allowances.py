from decimal import Decimal

EXEMPTION_LIMIT = Decimal("600.00")

def split_taxable(amount: Decimal):
    """
    Applies 600 exemption PER allowance type
    """
    if amount <= EXEMPTION_LIMIT:
        return {
            "non_taxable": amount,
            "taxable": Decimal("0.00"),
        }

    return {
        "non_taxable": EXEMPTION_LIMIT,
        "taxable": amount - EXEMPTION_LIMIT,
    }

def calculate_allowances(allowance_components):
    """
    allowance_components = {
        "Transport Allowance": Decimal("2000"),
        "Position Allowance": Decimal("3000"),
        "House Allowance": Decimal("2500"),
    }
    """
    total_taxable = Decimal("0")
    total_non_taxable = Decimal("0")

    breakdown = {}

    for name, amount in allowance_components.items():
        split = split_taxable(amount)
        total_taxable += split["taxable"]
        total_non_taxable += split["non_taxable"]

        breakdown[name] = split

    return {
        "total_taxable": total_taxable,
        "total_non_taxable": total_non_taxable,
        "breakdown": breakdown,
    }


