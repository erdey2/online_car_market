from rest_framework.exceptions import ValidationError
from rolepermissions.checkers import has_role
from ..models import Profile
import cloudinary
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from ..api.serializers import DealerProfileSerializer, BrokerProfileSerializer

class ProfileService:
    @staticmethod
    def get_visible_profiles(user):
        if has_role(user, ['super_admin', 'admin']):
            return Profile.objects.exclude(
                user__dealer_staff_assignments__isnull=False
            )
        return Profile.objects.filter(user=user)

    @staticmethod
    def get_my_profile(user):
        return Profile.objects.filter(user=user).first()

    @staticmethod
    def update_profile(profile, data):
        for attr, value in data.items():
            setattr(profile, attr, value)
        profile.save()
        return profile

    @staticmethod
    def upload_profile_image(image):
        try:
            result = cloudinary.uploader.upload(
                image,
                folder='profiles',
                resource_type='image',
                overwrite=True
            )
            return result['public_id']
        except Exception:
            raise ValidationError({"image": "Failed to upload image."})

    @staticmethod
    def update_related_profiles(profile, dealer_data=None, broker_data=None):
        if dealer_data and has_role(profile.user, 'dealer'):
            dealer_profile, _ = DealerProfile.objects.get_or_create(profile=profile)
            DealerProfileSerializer().update(dealer_profile, dealer_data)

        if broker_data and has_role(profile.user, 'broker'):
            broker_profile, _ = BrokerProfile.objects.get_or_create(profile=profile)
            BrokerProfileSerializer().update(broker_profile, broker_data)
