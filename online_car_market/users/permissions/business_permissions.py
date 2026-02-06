from rest_framework.permissions import BasePermission, SAFE_METHODS
from rolepermissions.checkers import has_role, has_permission

class IsAdminOrReadOnly(BasePermission):
    """Admins can verify/edit; others can only read their own."""
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return has_role(request.user, ["admin", "superadmin"]) or obj.uploaded_by == request.user

class IsHROrAdmin(BasePermission):
    """
    Allow HR role or Django staff/superuser to perform HR actions.
    """
    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False
        if u.is_staff or u.is_superuser:
            return True
        return has_role(u, "hr")

class IsHRorDealer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and has_role(request.user, ["hr", "dealer"]))

class IsOwnerOrHR(BasePermission):
    def has_object_permission(self, request, view, obj):
        return has_role(request.user, 'hr') or (obj.employee.user == request.user)

class CanPostCar(BasePermission):
    """
    Controls car posting and management permissions.
    - Dealers manage only their own cars.
    - Sellers manage cars only for their assigned dealer.
    - Brokers/Admins/SuperAdmins manage everything.
    - Buyers & anonymous users read only.
    """

    def has_permission(self, request, view):
        user = request.user

        # Read-only access for all
        if request.method in SAFE_METHODS:
            return True

        # Must be authenticated
        if not user.is_authenticated:
            return False

        # Sellers can write only if linked to a dealer
        if has_role(user, 'seller'):
            from online_car_market.dealers.models import DealerStaff
            return DealerStaff.objects.filter(user=user, role='seller').exists()

        # Dealers + high roles write freely
        if has_role(user, ['dealer', 'broker', 'admin', 'super_admin']):
            return True

        return False

    def has_object_permission(self, request, view, obj):
        """
        Object-level validation:
        Sellers & dealers can only modify cars belonging to their dealer.
        High roles modify everything.
        """

        user = request.user

        # Read-only always allowed
        if request.method in SAFE_METHODS:
            return True

        # High privilege roles can do anything
        if has_role(user, ['broker', 'admin', 'super_admin']):
            return True

        # Dealer can modify only their own cars
        if has_role(user, 'dealer'):
            return obj.dealer == user.dealer

        # Seller can modify only cars for their assigned dealer
        if has_role(user, 'seller'):
            from online_car_market.dealers.models import DealerStaff
            staff = DealerStaff.objects.filter(user=user, role='seller').first()
            if not staff:
                return False
            return obj.dealer == staff.dealer

        return False

class CanManageAccounting(BasePermission):
    """Only super_admin, admin, broker, dealer, or accountant can manage accounting data."""
    def has_permission(self, request, view):
        return has_role(request.user, ['super_admin', 'admin', 'broker', 'dealer', 'accountant', 'finance'])

class CanManageSales(BasePermission):
    """Only super_admin, admin, broker, or dealer can manage sales."""
    def has_permission(self, request, view):
        return has_role(request.user, ['super_admin', 'admin', 'broker', 'dealer', 'seller'])

class CanViewPayroll(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            has_permission(request.user, "view_payroll")
        )

class CanRunPayroll(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            has_permission(request.user, "run_payroll")
        )

class CanApprovePayroll(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            has_permission(request.user, "approve_payroll")
        )

class CanViewSalesData(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and (
                has_permission(request.user, 'view_accounting') or
                has_permission(request.user, 'view_sales_dashboard') or
                has_permission(request.user, 'view_finance')
            )
        )

class IsRatingOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user or has_role(request.user, ['super_admin', 'admin'])

class IsDealerWithManageStaff(BasePermission):
    def has_permission(self, request, view):
        return has_role(request.user, 'dealer') and has_permission(request.user, 'manage_staff') and hasattr(request.user.profile, 'dealer_profile')

class CanViewSalesData(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and (
                has_permission(request.user, 'view_accounting') or
                has_permission(request.user, 'view_sales_dashboard')
            )
        )

class IsERPUser(BasePermission):
    """
    Allow HR, Accountant, and Seller to manage contracts.
    HR has full access, others limited to draft creation.
    """
    def has_permission(self, request, view):
        from rolepermissions.checkers import has_role

        if not request.user or not request.user.is_authenticated:
            return False

        # Allow HR, Accountant, or Seller roles
        if (
            has_role(request.user, 'hr') or
            has_role(request.user, 'accountant') or
            has_role(request.user, 'seller')
        ):
            return True

        # Allow read-only access for admin/staff
        if request.method in SAFE_METHODS and request.user.is_staff:
            return True

        return False

class IsFinanceOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (
                has_role(request.user, "finance") or
                has_role(request.user, "admin") or
                has_role(request.user, "super_admin")
            )
        )


