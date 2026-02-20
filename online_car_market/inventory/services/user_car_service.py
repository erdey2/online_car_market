from ..models import Car
from rolepermissions.checkers import has_role

class UserCarService:
    @staticmethod
    def get_user_visible_cars(user):
        qs = Car.objects.select_related("dealer", "broker", "posted_by").prefetch_related("images", "bids")
        if has_role(user, ["super_admin", "admin"]):
            return qs
        if hasattr(user, "profile") and hasattr(user.profile, "dealer_profile"):
            return qs.filter(dealer=user.profile.dealer_profile)
        if hasattr(user, "profile") and hasattr(user.profile, "broker_profile"):
            return qs.filter(broker=user.profile.broker_profile)
        seller_record = user.dealer_staff_assignments.filter(role="seller").first()
        if seller_record:
            return qs.filter(dealer=seller_record.dealer, posted_by=user)
        return qs.none()
