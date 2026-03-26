from django.db import transaction
from rest_framework import serializers
from rolepermissions.checkers import has_role
from online_car_market.buyers.models import BuyerProfile, LoyaltyProgram
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.users.models import Profile, User
from online_car_market.users.models import Profile
import logging

logger = logging.getLogger(__name__)

class LoyaltyProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyProgram
        fields = ['id', 'points', 'reward', 'created_at']
        read_only_fields = ['id', 'points', 'reward', 'created_at']

class BuyerProfileSerializer(serializers.ModelSerializer):
    loyalty_programs = LoyaltyProgramSerializer(many=True, read_only=True)

    class Meta:
        model = BuyerProfile
        fields = ['loyalty_points', 'loyalty_programs']
        read_only_fields = ['loyalty_points', 'loyalty_programs']

class UpgradeToDealerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ['company_name', 'license_number', 'tax_id', 'telebirr_account']

    def validate(self, attrs):
        user = self.context['request'].user

        if user.role == User.Role.DEALER:
            raise serializers.ValidationError("User is already a dealer.")

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user

        profile, _ = Profile.objects.get_or_create(user=user)

        existing = DealerProfile.objects.filter(profile=profile).first()

        # CASE 1: existing application
        if existing:
            if existing.status in [
                DealerProfile.Status.PENDING,
                DealerProfile.Status.APPROVED,
                DealerProfile.Status.SUSPENDED,
            ]:
                raise serializers.ValidationError(
                    f"Application already exists with status '{existing.status}'"
                )

            # CASE 2: RE-APPLICATION
            if existing.status == DealerProfile.Status.REJECTED:
                existing.status = DealerProfile.Status.PENDING
                existing.reviewed_by = None
                existing.reviewed_at = None
                existing.rejection_reason = None

                for attr, value in validated_data.items():
                    setattr(existing, attr, value)

                existing.save()

                return existing

        # CASE 3: NEW APPLICATION
        dealer = DealerProfile.objects.create(
            profile=profile,
            status=DealerProfile.Status.PENDING,
            **validated_data
        )

        return dealer

class UpgradeToBrokerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerProfile
        fields = ['national_id', 'telebirr_account']

    def validate(self, attrs):
        user = self.context['request'].user

        if user.role == User.Role.BROKER:
            raise serializers.ValidationError("User is already a broker.")

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user

        profile, _ = Profile.objects.get_or_create(user=user)

        existing = BrokerProfile.objects.filter(profile=profile).first()

        # CASE 1: existing application
        if existing:
            if existing.status in [
                BrokerProfile.Status.PENDING,
                BrokerProfile.Status.APPROVED,
                BrokerProfile.Status.SUSPENDED,
            ]:
                raise serializers.ValidationError(
                    f"Application already exists with status '{existing.status}'"
                )

            # CASE 2: RE-APPLICATION
            if existing.status == BrokerProfile.Status.REJECTED:
                existing.status = BrokerProfile.Status.PENDING
                existing.reviewed_by = None
                existing.reviewed_at = None
                existing.rejection_reason = None

                for attr, value in validated_data.items():
                    setattr(existing, attr, value)

                existing.save()

                return existing

        # CASE 3: NEW APPLICATION
        broker = BrokerProfile.objects.create(
            profile=profile,
            status=BrokerProfile.Status.PENDING,
            **validated_data
        )

        return broker

class VerifyDealerSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField()

    class Meta:
        model = DealerProfile
        fields = ['is_verified']

    def validate_is_verified(self, value):
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify dealers.")
        return value
