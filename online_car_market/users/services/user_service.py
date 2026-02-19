from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from ..models import Profile
from rolepermissions.checkers import has_role
from rolepermissions.exceptions import RoleDoesNotExist
from rolepermissions.roles import assign_role, remove_role, get_user_roles

from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.buyers.models import BuyerProfile

User = get_user_model()

class UserService:

    @staticmethod
    def get_buyers():
        return [user for user in User.objects.all() if has_role(user, 'buyer')]

    @staticmethod
    def register_user(validated_data):
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        validated_data.pop('confirm_password')

        user = User.objects.create_user(**validated_data)

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.first_name = first_name
        profile.last_name = last_name
        profile.save()

        try:
            assign_role(user, 'buyer')
            BuyerProfile.objects.get_or_create(profile=profile)
        except RoleDoesNotExist:
            raise serializers.ValidationError("Role buyer does not exist.")

        return user

    @staticmethod
    @transaction.atomic
    def assign_role_to_user(user, role):
        current_roles = [r.get_name() for r in get_user_roles(user)]

        for current_role in current_roles:
            remove_role(user, current_role)

        assign_role(user, role)

        profile, _ = Profile.objects.get_or_create(user=user)

        if role == 'buyer':
            BuyerProfile.objects.get_or_create(profile=profile)

        elif role == 'dealer':
            DealerProfile.objects.get_or_create(
                profile=profile,
                defaults={
                    'company_name': user.email,
                    'license_number': '',
                    'telebirr_account': ''
                }
            )

        elif role == 'broker':
            BrokerProfile.objects.get_or_create(
                profile=profile,
                defaults={
                    'national_id': f"ID_{user.id}",
                    'telebirr_account': ''
                }
            )

        return user
