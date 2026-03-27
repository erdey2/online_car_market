from rest_framework.permissions import BasePermission, SAFE_METHODS
from online_car_market.dealers.models import DealerStaff

def has_any_role(user, roles):
    return user.is_authenticated and user.role in roles

class IsAdminOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == "admin" or obj.uploaded_by == request.user

class IsHROrAdmin(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return u.is_authenticated and (u.is_staff or u.is_superuser or u.role == "hr")

class IsHRorDealer(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["hr", "dealer"])

class IsOwnerOrHR(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.role == "hr" or obj.employee.user == request.user

class CanPostCar(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if request.method in SAFE_METHODS:
            return True

        if not user.is_authenticated:
            return False

        # Seller must belong to dealer
        if user.role == "seller":
            return user.dealer_staff_assignments.filter(role="seller").exists()

        return user.role in ["dealer", "broker", "admin"]

    def has_object_permission(self, request, view, obj):
        user = request.user

        if request.method in SAFE_METHODS:
            return True

        # High roles
        if user.role in ["admin", "broker"]:
            return True

        # Dealer → only own cars
        if user.role == "dealer":
            return (
                hasattr(user.profile, "dealer_profile") and
                obj.dealer == user.profile.dealer_profile
            )

        # Seller → only assigned dealer
        if user.role == "seller":
            staff = user.dealer_staff_assignments.filter(role="seller").first()
            return staff and obj.dealer == staff.dealer

        return False

class CanManageAccounting(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["admin", "broker", "dealer", "accountant", "finance"])

class CanManageSales(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["admin", "broker", "dealer", "seller"])

class CanViewPayroll(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["admin", "hr", "accountant"])

class CanRunPayroll(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["admin", "hr"])

class CanApprovePayroll(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["admin"])

class CanViewSalesData(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["admin", "accountant", "seller", "finance"])

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

        if user.role in ["hr", "accountant", "seller"]:
            return True

        if request.method in SAFE_METHODS and user.is_staff:
            return True

        return False

class IsFinanceOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, ["finance", "admin"])


class IsDealerOrStaff(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        profile = getattr(user, "profile", None)
        if not profile:
            return False

        if hasattr(profile, "dealer_profile"):
            return True

        return DealerStaff.objects.filter(user=user).exists()

class IsERPUsers(BasePermission):
    def has_permission(self, request, view):
        return has_any_role(request.user, [
            "dealer",
            "seller",
            "hr",
            "accountant",
            "admin"
        ])

class CanViewInventory(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        return (
            user.role in ["admin", "dealer", "broker"] or
            user.dealer_staff_assignments.filter(role="seller").exists()
        )
