from rest_framework import serializers
from rolepermissions.checkers import has_role
from rolepermissions.roles import assign_role

from ..models import Broker, BrokerListing
from online_car_market.users.models import User
from online_car_market.inventory.models import Car
from online_car_market.inventory.api.serializers import CarSerializer
import re
import bleach

class BrokerSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Broker
        fields = ['id', 'user', 'name', 'contact', 'commission_rate', 'national_id', 'telebirr_account', 'is_verified', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Sanitize and validate name."""
        if not value:
            raise serializers.ValidationError("Name is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Name cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z\s&-]+$', cleaned_value):
            raise serializers.ValidationError("Name can only contain letters, spaces, ampersands, or hyphens.")
        return cleaned_value

    def validate_contact(self, value):
        """Validate and sanitize Ethiopian phone number."""
        if not value:
            raise serializers.ValidationError("Contact is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if not re.match(r'^\+251[79]\d{8}$', cleaned_value):
            raise serializers.ValidationError("Contact must be a valid Ethiopian phone number (e.g., +251912345678).")
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Contact cannot exceed 100 characters.")
        return cleaned_value

    def validate_commission_rate(self, value):
        """Validate commission rate is between 0 and 100."""
        if not 0 <= value <= 100:
            raise serializers.ValidationError("Commission rate must be between 0 and 100.")
        return value

    def validate_national_id(self, value):
        """Sanitize and validate national ID (16 digits)."""
        if not value:
            raise serializers.ValidationError("National ID is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if not re.match(r'^\d{16}$', cleaned_value):
            raise serializers.ValidationError("National ID must be a 16-digit number.")
        if len(cleaned_value) > 16:
            raise serializers.ValidationError("National ID cannot exceed 16 characters.")
        if self.instance is None and Broker.objects.filter(national_id=cleaned_value).exists():
            raise serializers.ValidationError("A broker with this national ID already exists.")
        if self.instance and self.instance.national_id != cleaned_value and Broker.objects.filter(national_id=cleaned_value).exists():
            raise serializers.ValidationError("A broker with this national ID already exists.")
        return cleaned_value

    def validate_telebirr_account(self, value):
        """Validate and sanitize Ethiopian phone number for Telebirr."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if not re.match(r'^\+251[79]\d{8}$', cleaned_value):
                raise serializers.ValidationError("Telebirr account must be a valid Ethiopian phone number (e.g., +251912345678).")
            if len(cleaned_value) > 100:
                raise serializers.ValidationError("Telebirr account cannot exceed 100 characters.")
            return cleaned_value
        return value

    def validate_is_verified(self, value):
        """Ensure only super_admin or admin can set is_verified."""
        user = self.context['request'].user
        if value and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify brokers.")
        return value

    def validate_user(self, value):
        """Ensure user has broker role."""
        if not has_role(value, 'broker'):
            raise serializers.ValidationError("The assigned user must have the broker role.")
        return value

    def validate(self, data):
        """Ensure only super_admin, admin, or the broker can manage their profile."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'broker']):
            raise serializers.ValidationError("Only super admins, admins, or brokers can create broker profiles.")
        if self.instance and self.instance.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins, admins, or the broker can update this profile.")
        return data

class BrokerListingSerializer(serializers.ModelSerializer):
    broker = serializers.PrimaryKeyRelatedField(queryset=Broker.objects.all())
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())
    broker_display = BrokerSerializer(source='broker', read_only=True)
    car_display = CarSerializer(source='car', read_only=True)

    class Meta:
        model = BrokerListing
        fields = ['id', 'broker', 'car', 'broker_display', 'car_display', 'commission', 'created_at']
        read_only_fields = ['id', 'created_at', 'broker_display', 'car_display']

    def validate_commission(self, value):
        """Ensure commission is non-negative and reasonable."""
        if value < 0:
            raise serializers.ValidationError("Commission cannot be negative.")
        if value > 1000000:
            raise serializers.ValidationError("Commission cannot exceed 1,000,000.")
        return value

    def validate_car(self, value):
        """Ensure car is available or reserved."""
        if value.status not in ['available', 'reserved']:
            raise serializers.ValidationError("The car must be available or reserved for listing.")
        return value

    def validate_broker(self, value):
        """Ensure broker has broker role."""
        if not has_role(value.user, 'broker'):
            raise serializers.ValidationError("The assigned broker must have the broker role.")
        return value

    def validate(self, data):
        """Ensure only super_admin, admin, or the broker can manage listings."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'broker']):
            raise serializers.ValidationError("Only super admins, admins, or brokers can create broker listings.")
        if self.instance and self.instance.broker.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins, admins, or the broker can update this listing.")
        return data

class UpgradeToBrokerSerializer(BrokerSerializer):
    class Meta(BrokerSerializer.Meta):
        fields = ['name', 'contact', 'commission_rate', 'national_id', 'telebirr_account']

    def create(self, validated_data):
        user = self.context['request'].user
        broker = Broker.objects.create(user=user, **validated_data)
        assign_role(user, 'broker')
        return broker

class VerifyBrokerSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField()

    class Meta:
        model = Broker
        fields = ['is_verified']

    def validate_is_verified(self, value):
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify brokers.")
        return value
