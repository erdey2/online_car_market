def can_run_payroll(payroll_run):
    return payroll_run.status == "draft"

def can_post_payroll(payroll_run):
    return payroll_run.status == "approved"
