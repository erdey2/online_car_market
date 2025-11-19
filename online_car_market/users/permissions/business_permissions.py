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

class CanPostCar(BasePermission):
    """
    Custom permission controlling who can post or manage cars.
    - Dealers can post/manage their own cars.
    - Sellers can post/manage cars only for their assigned dealer.
    - Brokers, Admins, and SuperAdmins have full access.
    - Buyers or unauthenticated users can only read.
    """
    def has_permission(self, request, view):
        user = request.user

        # Allow read-only access for everyone
        if request.method in SAFE_METHODS:
            return True

        # Must be authenticated for write actions
        if not user.is_authenticated:
            return False

        # Sellers can post only if they belong to a dealer
        if has_role(user, 'seller'):
            from online_car_market.dealers.models import DealerStaff
            return DealerStaff.objects.filter(
                user=user,
                role='seller'
            ).exists()

        # Dealers, brokers, admins, and super_admins can post/manage cars freely
        if has_role(user, ['dealer', 'broker', 'admin', 'super_admin']):
            return True

        # Otherwise, no permission
        return False

class CanManageAccounting(BasePermission):
    """Only super_admin, admin, broker, dealer, or accountant can manage accounting data."""
    def has_permission(self, request, view):
        return has_role(request.user, ['super_admin', 'admin', 'broker', 'dealer', 'accountant'])

class CanManageSales(BasePermission):
    """Only super_admin, admin, broker, or dealer can manage sales."""
    def has_permission(self, request, view):
        return has_role(request.user, ['super_admin', 'admin', 'broker', 'dealer', 'seller'])

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

