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
        return User.objects.filter(role=User.Role.BUYER).select_related(
            "profile",
            "profile__buyer_profile",
        )

    @staticmethod
    def register_user(validated_data):
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        contact = validated_data.pop("contact", "")

        validated_data.pop("confirm_password")

        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            role=User.Role.BUYER,
            **validated_data
        )

        Profile.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            contact=contact,
        )

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
