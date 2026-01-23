from decimal import Decimal

def calculate_pension(basic_salary):
    return {
        "employee": basic_salary * Decimal("0.07"),
        "employer": basic_salary * Decimal("0.11"),
    }
