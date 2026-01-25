from online_car_market.payroll.models import PayrollItem

def get_payslip_for_employee(employee, period):
    return PayrollItem.objects.filter(
        employee=employee,
        payroll_run__period=period,
        payroll_run__status="posted"
    ).select_related("employee")
