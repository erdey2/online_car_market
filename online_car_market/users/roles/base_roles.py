from rolepermissions.roles import AbstractUserRole

class SuperAdmin(AbstractUserRole):
    available_permissions = {
        'manage_users': True,
        'manage_buyers': True,
        'manage_brokers': True,
        'manage_dealers': True,
        'manage_inventory': True,
        'manage_sellers': True,
        'manage_accountants': True,
        'verify_car': True,
        'verify_broker': True,
        'verify_dealer': True,
        'view_analytics': True,
        'run_payroll': True,
        'approve_payroll': True,
        'lock_payroll': True,
    }

class Admin(AbstractUserRole):
    available_permissions = {
        'view_admin_dashboard': True,
        'manage_buyers': True,
        'manage_brokers': True,
        'manage_dealers': True,
        'manage_inventory': True,
        'manage_sellers': True,
        'view_accounting': True,
        'verify_car': True,
        'verify_broker': True,
        'verify_dealer': True,
        'run_payroll': True,
    }

class Dealer(AbstractUserRole):
    available_permissions = {
        'view_dealer_dashboard': True,
        'view_own_dealer_profile': True,
        'edit_own_dealer_profile': True,
        'manage_own_inventory': True,
        'view_cars': True,
        'manage_staff': True,
    }

class Broker(AbstractUserRole):
    available_permissions = {
        'view_broker_dashboard': True,
        'view_own_broker_profile': True,
        'edit_own_broker_profile': True,
        'view_cars': True,
        'post_car': True,
    }

class Buyer(AbstractUserRole):
    available_permissions = {
        'view_buyer_dashboard': True,
        'view_own_buyer_profile': True,
        'edit_own_buyer_profile': True,
        'view_cars': True,
        'bid_on_car': True,
        'purchase_car': True,
    }

class HR(AbstractUserRole):
    available_permissions = {
        'manage_employees': True,
        'manage_contracts': True,
        'manage_attendance': True,
        'manage_leaves': True,
        'view_hr_reports': True,
        'view_payroll': True,
        'run_payroll': False,
        'approve_payroll': False,
    }

class Seller(AbstractUserRole):
    available_permissions = {
        'view_sales_dashboard': True,
        'view_cars': True,
        'manage_sales': True,
        'view_own_sales': True,
        'post_car': True,
        'request_leave': True,
        'view_own_contract': True,
    }

class Accountant(AbstractUserRole):
    available_permissions = {
        'view_accounting': True,
        'manage_accounting': True,
        'request_leave': True,
        'view_own_contract': True,
        'view_payroll': True,
        'view_payroll_report': True,
    }

class Finance(AbstractUserRole):
    """
        Finance controls payroll & financial validation
        """
    available_permissions = {
        # Read
        "view_finance": True,
        "view_payroll": True,
        "view_payroll_report": True,
        "view_salary_breakdown": True,

        # Control
        "run_payroll": True,
        "approve_payroll": True,
        "lock_payroll": True,

        # Adjustments
        "adjust_overtime": True,
        "adjust_allowances": True,

        # Explicit NO
        "manage_employees": False,
        "manage_salary_components": False,
    }


