from rest_framework.permissions import BasePermission
from rolepermissions.checkers import has_role

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and has_role(request.user, 'super_admin')

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and has_role(request.user, 'admin')

class IsDealer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and has_role(request.user, 'dealer')

class IsSuperAdminOrAdminOrDealer(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (has_role(request.user, 'super_admin') or
             has_role(request.user, 'admin') or
             has_role(request.user, 'dealer'))
        )

