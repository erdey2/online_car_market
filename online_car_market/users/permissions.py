from rest_framework.permissions import BasePermission
from rolepermissions.checkers import has_role
from rolepermissions.roles import AbstractUserRole
from rolepermissions.roles import get_user_roles
from rolepermissions.checkers import has_permission
import logging

logger = logging.getLogger(__name__)

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'super_admin')

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'admin')

class IsDealer(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'dealer')

class IsSuperAdminOrAdminOrDealerOrBroker(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'super_admin') or
             has_role(request.user, 'admin') or
             has_role(request.user, 'dealer') or
             has_role(request.user, 'broker'))
        )

class IsSuperAdminOrAdminOrDealer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'super_admin') or
             has_role(request.user, 'admin') or
             has_role(request.user, 'dealer'))
        )

class IsSuperAdminOrAdminOrBuyer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'super_admin') or
             has_role(request.user, 'admin') or
             has_role(request.user, 'buyer'))
        )

class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'super_admin') or has_role(request.user, 'admin'))
        )

class IsBroker(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'broker')

class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'buyer')

class CanPostCar(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            has_permission(request.user, 'post_car')
        )

class CanViewSalesData(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and (
                has_permission(request.user, 'view_accounting') or
                has_permission(request.user, 'view_sales_dashboard')
            )
        )

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
    }

class Dealer(AbstractUserRole):
    available_permissions = {
        'view_dealer_dashboard': True,
        'view_own_dealer_profile': True,
        'edit_own_dealer_profile': True,
        'manage_own_inventory': True,
        'view_cars': True,
        'post_car': True,
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

class Seller(AbstractUserRole):
    available_permissions = {
        'view_sales_dashboard': True,
        'view_cars': True,
        'manage_sales': True,
        'view_own_sales': True,
        'post_car': True,
    }

class Accountant(AbstractUserRole):
    available_permissions = {
        'view_accounting': True,
        'manage_accounting': True,
    }
