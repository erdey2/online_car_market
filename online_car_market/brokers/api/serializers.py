from rest_framework import serializers
from online_car_market.brokers.models import Broker
from online_car_market.inventory.api.serializers import CarSerializer
from online_car_market.brokers.models import BrokerListing
from rolepermissions.checkers import has_role
import re

class BrokerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Broker
        fields = ['id', 'name', 'contact', 'commission_rate',
                  'national_id', 'telebirr_account', 'is_verified',
                  'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Ensure name is valid."""
        if not value:
            raise serializers.ValidationError("Name is required.")
        if len(value) > 100:
            raise serializers.ValidationError("Name cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s&-]+$', value):
            raise serializers.ValidationError("Name can only contain letters, numbers, spaces, ampersands, or hyphens.")
        return value

    def validate_contact(self, value):
        """Ensure contact is a valid Ethiopian phone number."""
        if not re.match(r'^\+251[79]\d{8}$', value):
            raise serializers.ValidationError("Contact must be a valid Ethiopian phone number (e.g., +251912345678).")
        return value

    def validate_commission_rate(self, value):
        """Ensure commission_rate is between 0 and 100."""
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Commission rate must be between 0 and 100.")
        return value

    def validate_national_id(self, value):
        """Ensure national_id is unique and follows format (e.g., ET12345678)."""
        if not re.match(r'^[0-9]{16}$', value):
            raise serializers.ValidationError("National ID must be a 16 digit number.")
        if self.instance is None and Broker.objects.filter(national_id=value).exists():
            raise serializers.ValidationError("A broker with this national ID already exists.")
        return value

    def validate_telebirr_account(self, value):
        """Ensure telebirr_account is a valid Ethiopian phone number."""
        if value and not re.match(r'^\+251[79]\d{8}$', value):
            raise serializers.ValidationError(
                "Telebirr account must be a valid Ethiopian phone number (e.g., +251912345678).")
        return value

    def validate_is_verified(self, value):
        """Ensure only admins can set is_verified."""
        user = self.context['request'].user
        if value and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only admins or super admins can verify brokers.")
        return value

    def validate(self, data):
        """Ensure user has broker role."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'broker']):
            raise serializers.ValidationError("Only brokers, admins, or super admins can create broker profiles.")
        if self.instance and self.instance.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the profile owner or admins can update this profile.")
        return data

class BrokerListingSerializer(serializers.ModelSerializer):
    broker = BrokerSerializer(read_only=True)
    car = CarSerializer(read_only=True)

    class Meta:
        model = BrokerListing
        fields = ['id', 'broker', 'car', 'commission', 'created_at']
        read_only_fields = ['id', 'broker', 'car', 'created_at']

    def validate_commission(self, value):
        """Ensure commission is non-negative and reasonable."""
        if value < 0:
            raise serializers.ValidationError("Commission cannot be negative.")
        if value > 1000000:
            raise serializers.ValidationError("Commission cannot exceed 1,000,000.")
        return value

    def validate(self, data):
        """Ensure only brokers or admins can create/update listings."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'broker']):
            raise serializers.ValidationError("Only brokers, admins, or super admins can create broker listings.")
        if self.instance and self.instance.broker.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the listing owner or admins can update this listing.")
        return data
