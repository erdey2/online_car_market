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

        # Anonymous → like buyer
        if not user.is_authenticated:
            return qs.filter(verification_status="verified")

        role = user.role
        profile = getattr(user, "profile", None)

        # Admins → all cars
        if role in ["admin", "super_admin"]:
            return qs

        # SELLER
        staff_qs = getattr(user, "dealer_staff_assignments", None)
        if staff_qs:
            seller_record = staff_qs.filter(role="seller").first()
            if seller_record:
                return qs.filter(dealer=seller_record.dealer)

        # Dealer → own cars
        dealer_profile = getattr(profile, "dealer_profile", None)
        if role == "dealer" and dealer_profile:
            return qs.filter(dealer=dealer_profile)

        # Broker → own cars
        broker_profile = getattr(profile, "broker_profile", None)
        if role == "broker" and broker_profile:
            return qs.filter(broker=broker_profile)

        # Buyer → only verified cars
        if role == "buyer":
            return qs.filter(verification_status="verified")

        return qs.none()

    @staticmethod
    def can_user_access_car(user, car):
        """
        Optimized access check (no DB hit)
        """

        # Anonymous
        if not user.is_authenticated:
            return car.verification_status == "verified"

        role = user.role
        profile = getattr(user, "profile", None)

        # Admins
        if role in ["admin", "super_admin"]:
            return True

        # SELLER
        staff_qs = getattr(user, "dealer_staff_assignments", None)
        if staff_qs:
            seller_record = staff_qs.filter(role="seller").first()
            if seller_record:
                return car.dealer_id == seller_record.dealer_id

        # Dealer
        dealer_profile = getattr(profile, "dealer_profile", None)
        if role == "dealer" and dealer_profile:
            return car.dealer_id == dealer_profile.id

        # Broker
        broker_profile = getattr(profile, "broker_profile", None)
        if role == "broker" and broker_profile:
            return car.broker_id == broker_profile.id

        # Buyer
        if role == "buyer":
            return car.verification_status == "verified"

        return False
