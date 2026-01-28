from online_car_market.payroll.models import PayrollItem

def get_latest_payslip(employee, period=None):
    qs = PayrollItem.objects.filter(
        employee=employee,
        payroll_run__status__in=["approved", "posted"]
    )

    if period:
        year, month, _ = period.split("-")
        qs = qs.filter(
            payroll_run__period__year=year,
            payroll_run__period__month=month
        )

    return qs.order_by(
        "-payroll_run__period",
        "-payroll_run__created_at"
    ).first()


