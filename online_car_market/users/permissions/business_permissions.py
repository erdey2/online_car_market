from rest_framework.permissions import BasePermission, SAFE_METHODS
from online_car_market.dealers.models import DealerStaff

# HELPERS
def is_staff(user, roles=None):
    if not user.is_authenticated:
        return False

    staff = (
        DealerStaff.objects
        .select_related("dealer")  # helps later usage
        .filter(user=user)
        .first()
    )

    if not staff:
        return False

    if roles:
        return staff.role in roles

    return True

def has_any_role(user, roles):
    return user.is_authenticated and user.role in roles

# BASIC
class IsAdminOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == "admin" or obj.uploaded_by == request.user

class IsHROrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and
            (user.role == "admin" or is_staff(user, ["hr"]))
        )

class IsHRorDealer(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        return (
            user.role == "dealer" or
            is_staff(user, ["hr"])
        )

class IsOwnerOrHR(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.user == obj.employee.user or
            is_staff(request.user, ["hr"])
        )

# CAR / SALES
class CanPostCar(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if request.method in SAFE_METHODS:
            return True

        if not user.is_authenticated:
            return False

        # Dealer / Broker / Admin
        if user.role in ["dealer", "broker", "admin"]:
            return True

        # Seller staff
        return is_staff(user, ["seller"])

    def has_object_permission(self, request, view, obj):
        user = request.user

        if request.method in SAFE_METHODS:
            return True

        if user.role in ["admin", "broker"]:
            return True

        # Dealer → own cars
        if user.role == "dealer":
            return (
                hasattr(user.profile, "dealer_profile") and
                obj.dealer == user.profile.dealer_profile
            )

        # Seller → dealer cars
        staff = DealerStaff.objects.filter(user=user, role="seller").first()
        return staff and obj.dealer == staff.dealer

# ACCOUNTING / FINANCE
class CanManageAccounting(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user.role in ["admin", "super_admin", "dealer"] or
            is_staff(user, ["accountant", "finance"])
        )

class CanManageSales(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and user.role in ["admin", "dealer", "broker"] or
            is_staff(user, ["seller"])
        )

class CanViewPayroll(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        return (
            user.role == "admin" or
            is_staff(user, ["hr", "accountant", "finance"])
        )

class CanRunPayroll(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        return (
            user.role == "admin" or
            is_staff(user, ["hr"])
        )

class CanApprovePayroll(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated and
            user.role == "admin"
        )

class CanPostPayroll(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        return (
            user.role == "admin" or
            is_staff(user, ["finance"])
        )

class CanViewSalesData(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.role == "admin" or
            is_staff(user, ["accountant", "seller", "finance"])
        )

# GENERAL
class IsRatingOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user or request.user.role == "admin"

class IsDealerWithManageStaff(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and
            user.role == "dealer" and
            hasattr(user.profile, "dealer_profile")
        )

class IsHrAccountantSeller(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        if is_staff(user, ["hr", "accountant", "seller"]):
            return True

        return request.method in SAFE_METHODS

class IsFinanceOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.role == "admin" or
            is_staff(request.user, ["finance"])
        )

class IsDealerOrStaff(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and
            (user.role == "dealer" or is_staff(user))
        )

class IsERPUsers(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and
            (user.role in ["dealer", "admin"] or is_staff(user))
        )

class CanViewInventory(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user.role in ["admin", "dealer", "broker"] or
            is_staff(user, ["seller"])
        )
