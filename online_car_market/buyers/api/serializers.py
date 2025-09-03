from rest_framework import serializers
from rolepermissions.checkers import has_role
from rolepermissions.roles import assign_role
from online_car_market.buyers.models import BuyerProfile, LoyaltyProgram
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.users.api.serializers import DealerProfileSerializer, BrokerProfileSerializer
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

class UpgradeToDealerSerializer(DealerProfileSerializer):
    class Meta(DealerProfileSerializer.Meta):
        fields = ['company_name', 'license_number', 'tax_id', 'telebirr_account']

    def validate(self, data):
        user = self.context['request'].user
        if has_role(user, 'dealer'):
            raise serializers.ValidationError("User is already a dealer.")
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        profile, _ = Profile.objects.get_or_create(user=user)
        dealer = DealerProfile.objects.create(profile=profile, **validated_data)
        assign_role(user, 'dealer')
        logger.info(f"User {user.email} upgraded to dealer")
        return dealer

class UpgradeToBrokerSerializer(BrokerProfileSerializer):
    class Meta(BrokerProfileSerializer.Meta):
        fields = ['national_id', 'telebirr_account']

    def validate(self, data):
        user = self.context['request'].user
        if has_role(user, 'broker'):
            raise serializers.ValidationError("User is already a broker.")
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        profile, _ = Profile.objects.get_or_create(user=user)
        broker = BrokerProfile.objects.create(profile=profile, **validated_data)
        assign_role(user, 'broker')
        logger.info(f"User {user.email} upgraded to broker")
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
