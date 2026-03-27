from ..models import Car

class UserCarService:
    @staticmethod
    def get_user_visible_cars(user):
        qs = Car.objects.select_related(
            "dealer", "broker", "posted_by"
        ).prefetch_related("images", "bids")

        if user.role in ["super_admin", "admin"]:
            return qs

        profile = getattr(user, "profile", None)

        # Dealer
        dealer_profile = getattr(profile, "dealer_profile", None)
        if dealer_profile:
            return qs.filter(dealer=dealer_profile)

        # Broker
        broker_profile = getattr(profile, "broker_profile", None)
        if broker_profile:
            return qs.filter(broker=broker_profile)

        # Seller
        seller_record = user.dealer_staff_assignments.filter(role="seller").first()
        if seller_record:
            return qs.filter(
                dealer=seller_record.dealer,
                posted_by=user
            )

        return qs.none()
