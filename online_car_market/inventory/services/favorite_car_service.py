from rest_framework.exceptions import PermissionDenied, NotFound
from rolepermissions.checkers import has_role
from ..models import FavoriteCar

class FavoriteCarService:
    @staticmethod
    def check_buyer_role(user):
        if not has_role(user, 'buyer'):
            raise PermissionDenied("User does not have buyer role.")

    @staticmethod
    def list_favorites(user, queryset):
        FavoriteCarService.check_buyer_role(user)
        return queryset.filter(user=user)

    @staticmethod
    def create_favorite(user, data, serializer_class):
        FavoriteCarService.check_buyer_role(user)
        serializer = serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return serializer.data

    @staticmethod
    def retrieve_favorite(user, pk, queryset, serializer_class):
        FavoriteCarService.check_buyer_role(user)
        try:
            favorite = queryset.get(pk=pk)
        except FavoriteCar.DoesNotExist:
            raise NotFound("Favorite car not found or you do not have permission to view it.")
        serializer = serializer_class(favorite)
        return serializer.data

    @staticmethod
    def destroy_favorite(user, pk, queryset):
        FavoriteCarService.check_buyer_role(user)
        try:
            favorite = queryset.get(pk=pk)
        except FavoriteCar.DoesNotExist:
            raise NotFound("Favorite car not found or you do not have permission to delete it.")
        favorite.delete()
