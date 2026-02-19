from rest_framework.permissions import BasePermission
from rolepermissions.checkers import has_role

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'super_admin')

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'admin')

class IsDealer(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'dealer')

class IsBroker(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'broker')

class IsHR(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'hr')

class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'buyer')

class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_superuser or request.user.is_staff
        )

class IsSuperAdminOrAdminOrDealer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'super_admin') or
             has_role(request.user, 'admin') or
             has_role(request.user, 'dealer'))
        )

class IsSuperAdminOrAdminOrBroker(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'super_admin') or
             has_role(request.user, 'admin') or
             has_role(request.user, 'broker')
             )
        )

class IsSuperAdminOrAdminOrDealerOrBroker(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'super_admin') or
             has_role(request.user, 'admin') or
             has_role(request.user, 'dealer') or
             has_role(request.user, 'broker'))
        )

class IsSuperAdminOrAdminOrBuyer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'super_admin') or
             has_role(request.user, 'admin') or
             has_role(request.user, 'buyer'))
        )

class IsDealerOrAccountant(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'dealer') or
             has_role(request.user, 'accountant'))
        )

class IsDealerOrHR(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'dealer') or
             has_role(request.user, 'HR'))
        )

class IsDealerBrokerOrSeller(BasePermission):
    message = "Only dealers, brokers or sellers can create or edit inspections."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Allow brokers, dealers, or sellers
        return has_role(request.user, ["broker", "dealer", "seller"])

class IsFinance(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and has_role(request.user, "finance")



