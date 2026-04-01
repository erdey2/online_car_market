from ..models import Car


class UserCarService:

    @staticmethod
    def get_base_queryset():
        return Car.objects.select_related(
            "dealer", "broker", "posted_by"
        ).prefetch_related("images", "bids")

    @staticmethod
    def get_user_visible_cars(user):
        qs = UserCarService.get_base_queryset()

        if not user.is_authenticated:
            return qs.filter(status="verified")  # anonymous behaves like buyer

        role = user.role
        profile = getattr(user, "profile", None)

        # Admins → all cars
        if role in ["admin", "super_admin"]:
            return qs

        # Buyer → all VERIFIED cars
        if role == "buyer":
            return qs.filter(status="verified")

        # Dealer → own dealer cars
        dealer_profile = getattr(profile, "dealer_profile", None)
        if role == "dealer" and dealer_profile:
            return qs.filter(dealer=dealer_profile)

        # Broker → own cars
        broker_profile = getattr(profile, "broker_profile", None)
        if role == "broker" and broker_profile:
            return qs.filter(broker=broker_profile)

        # Seller → dealer cars (NOT only posted_by anymore)
        staff_qs = getattr(user, "dealer_staff_assignments", None)
        if role == "seller" and staff_qs:
            seller_record = staff_qs.filter(role="seller").first()
            if seller_record:
                return qs.filter(dealer=seller_record.dealer)

        return qs.none()

    @staticmethod
    def can_user_access_car(user, car):
        """
        Optimized access check (faster than queryset.exists())
        """

        if not user.is_authenticated:
            return car.status == "verified"

        role = user.role
        profile = getattr(user, "profile", None)

        if role in ["admin", "super_admin"]:
            return True

        if role == "buyer":
            return car.status == "verified"

        dealer_profile = getattr(profile, "dealer_profile", None)
        if role == "dealer" and dealer_profile:
            return car.dealer_id == dealer_profile.id

        broker_profile = getattr(profile, "broker_profile", None)
        if role == "broker" and broker_profile:
            return car.broker_id == broker_profile.id

        staff_qs = getattr(user, "dealer_staff_assignments", None)
        if role == "seller" and staff_qs:
            seller_record = staff_qs.filter(role="seller").first()
            if seller_record:
                return car.dealer_id == seller_record.dealer_id

        return False
