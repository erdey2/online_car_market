from rest_framework.permissions import BasePermission

def has_any_role(user, roles):
    return user.is_authenticated and user.role in roles

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "super_admin"

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"

class IsDealer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "dealer"

class IsBroker(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "broker"

class IsHR(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "hr"

class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "buyer"

class IsFinance(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "finance"

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

class IsDealerOrAccountant(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["dealer", "accountant"])

class IsDealerOrHR(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["dealer", "hr"])

class IsDealerBrokerOrSeller(BasePermission):
    message = "Only dealers, brokers or sellers can create or edit inspections."

    def has_permission(self, request, view):
        return has_any_role(request.user, ["dealer", "broker", "seller"])
