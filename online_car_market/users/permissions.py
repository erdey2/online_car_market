from rolepermissions.roles import AbstractUserRole

class SuperAdmin(AbstractUserRole):
    available_permissions = {
        'manage_users': True,
        'manage_buyers': True,
        'manage_brokers': True,
        'manage_dealers': True,
        'manage_inventory': True,
        'manage_sales': True,
        'manage_accounting': True,
    }

class Admin(AbstractUserRole):
    available_permissions = {
        'manage_buyers': True,
        'manage_brokers': True,
        'manage_dealers': True,
        'manage_inventory': True,
        'manage_sales': True,
        'view_accounting': True,
    }

class Sales(AbstractUserRole):
    available_permissions = {
        'view_cars': True,
        'manage_sales': True,
        'view_own_sales': True,
    }

class Accounting(AbstractUserRole):
    available_permissions = {
        'view_accounting': True,
        'manage_accounting': True,
    }

class Buyer(AbstractUserRole):
    available_permissions = {
        'view_own_buyer_profile': True,
        'edit_own_buyer_profile': True,
        'view_cars': True,
        'create_rating': True,
        'view_own_ratings': True,
        'view_own_loyalty': True,
    }

class Broker(AbstractUserRole):
    available_permissions = {
        'view_own_broker_profile': True,
        'edit_own_broker_profile': True,
        'view_cars': True,
        'create_broker_listing': True,
        'view_own_broker_listings': True,
    }

class Dealer(AbstractUserRole):
    available_permissions = {
        'view_own_dealer_profile': True,
        'edit_own_dealer_profile': True,
        'view_cars': True,
        'manage_own_car_listings': True,
    }
