from rest_framework.permissions import BasePermission
from online_car_market.users.permissions.business_permissions import is_staff

# GLOBAL ROLE CHECK
def has_any_role(user, roles):
    return user.is_authenticated and user.role in roles

# GLOBAL ROLES
class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["super_admin"])

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["admin"])

class IsDealer(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["dealer"])

class IsBroker(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["broker"])

class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["buyer"])

# STAFF ROLES
class IsHR(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and is_staff(request.user, ["hr"])

class IsFinance(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and is_staff(request.user, ["finance"])

# MIXED ROLES

class IsBuyerOrBroker(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["buyer", "broker"])

class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["super_admin", "admin"])

class IsSuperAdminOrAdminOrDealer(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["super_admin", "admin", "dealer"])

class IsSuperAdminOrAdminOrBroker(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["super_admin", "admin", "broker"])

class IsSuperAdminOrAdminOrDealerOrBroker(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["super_admin", "admin", "dealer", "broker"])

class IsSuperAdminOrAdminOrBuyer(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["super_admin", "admin", "buyer"])

# FIXED COMBINATIONS
class IsDealerOrAccountant(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and
            (
                user.role == "dealer" or
                is_staff(user, ["accountant"])
            )
        )

class IsDealerOrHR(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and
            (
                user.role == "dealer" or
                is_staff(user, ["hr"])
            )
        )

class IsDealerBrokerOrSeller(BasePermission):
    message = "Only dealers, brokers or sellers can create or edit inspections."

    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and
            (
                user.role in ["dealer", "broker"] or
                is_staff(user, ["seller"])
            )
        )
