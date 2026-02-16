from django.db.models import QuerySet
from online_car_market.sales.models import Sale
from online_car_market.dealers.models import DealerStaff, DealerProfile
from online_car_market.buyers.models import BuyerProfile
from online_car_market.brokers.models import BrokerProfile
from rolepermissions.checkers import has_role

class SaleService:

    @staticmethod
    def base_queryset() -> QuerySet:
        """
        Base optimized queryset for sales.
        """
        return Sale.objects.select_related("car", "broker", "buyer", "car__dealer")

    @staticmethod
    def get_sales_for_user(user) -> QuerySet:
        """
        Returns sales filtered by user role.
        """

        queryset = SaleService.base_queryset()

        if has_role(user, 'super_admin') or has_role(user, 'admin'):
            return queryset

        if has_role(user, 'broker'):
            try:
                broker_profile = BrokerProfile.objects.get(profile__user=user)
                return queryset.filter(broker=broker_profile)
            except BrokerProfile.DoesNotExist:
                return queryset.none()

        if has_role(user, 'dealer'):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
                return queryset.filter(car__dealer=dealer_profile)
            except DealerProfile.DoesNotExist:
                return queryset.none()

        if has_role(user, 'seller'):
            try:
                dealer_staff = DealerStaff.objects.get(user=user)
                return queryset.filter(car__dealer=dealer_staff.dealer)
            except DealerStaff.DoesNotExist:
                return queryset.none()

        if has_role(user, 'buyer'):
            try:
                buyer_profile = BuyerProfile.objects.get(profile__user=user)
                return queryset.filter(buyer=buyer_profile.profile.user)
            except BuyerProfile.DoesNotExist:
                return queryset.none()

        return queryset.none()
