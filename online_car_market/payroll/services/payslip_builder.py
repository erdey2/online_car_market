def build_payslip_json(payroll_item):
    earnings = []
    deductions = []

    for line in payroll_item.payrollline_set.all():
        item = {
            "name": line.component.name,
            "amount": str(line.amount),
        }

        if line.component.component_type == "earning":
            earnings.append(item)
        else:
            deductions.append(item)

    return {
        "employee": payroll_item.employee.id,
        "gross_earnings": str(payroll_item.gross_earnings),
        "total_deductions": str(payroll_item.total_deductions),
        "net_salary": str(payroll_item.net_salary),
        "earnings": earnings,
        "deductions": deductions,
    }
