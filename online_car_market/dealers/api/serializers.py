from rest_framework import serializers
from rolepermissions.checkers import has_role
from rolepermissions.roles import assign_role

from online_car_market.users.api.serializers import UserSerializer
from ..models import Dealer
import bleach
import re

class DealerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    # user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Dealer
        fields = ['id', 'user', 'company_name', 'license_number', 'address', 'telebirr_account', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Sanitize and validate name."""
        if not value:
            raise serializers.ValidationError("Name is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Name cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z\s-]+$', cleaned_value):
            raise serializers.ValidationError("Name can only contain letters, spaces, or hyphens.")
        return cleaned_value

    def validate_license_number(self, value):
        """Sanitize and validate license number."""
        if not value:
            raise serializers.ValidationError("License number is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 50:
            raise serializers.ValidationError("License number cannot exceed 50 characters.")
        if not re.match(r'^[a-zA-Z0-9-]+$', cleaned_value):
            raise serializers.ValidationError("License number can only contain letters, numbers, or hyphens.")
        return cleaned_value

    def validate_address(self, value):
        """Sanitize and validate address."""
        if not value:
            raise serializers.ValidationError("Address is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Address cannot exceed 100 characters.")
        return cleaned_value

    def validate_telebirr_account(self, value):
        """Validate and sanitize Ethiopian phone number for Telebirr."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if not re.match(r'^\+251[79]\d{8}$', cleaned_value):
                raise serializers.ValidationError(
                    "Telebirr account must be a valid Ethiopian phone number (e.g., +251912345678).")
            if len(cleaned_value) > 100:
                raise serializers.ValidationError("Telebirr account cannot exceed 100 characters.")
            return cleaned_value
        return value

    def validate_user(self, value):
        """Ensure user has dealer role."""
        if not has_role(value, 'dealer'):
            raise serializers.ValidationError("The assigned user must have the dealer role.")
        return value

    def validate(self, data):
        """Ensure only super_admin, admin, or the dealer can manage their profile."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'dealer']):
            raise serializers.ValidationError("Only super admins, admins, or dealers can create dealer profiles.")
        if self.instance and self.instance.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins, admins, or the dealer can update this profile.")
        return data

class UpgradeToDealerSerializer(DealerSerializer):
    class Meta(DealerSerializer.Meta):
        fields = ['company_name', 'phone', 'address', 'license_number', 'tax_id', 'telebirr_account', 'is_verified']

    def create(self, validated_data):
        user = self.context['request'].user
        dealer = Dealer.objects.create(user=user, **validated_data)
        assign_role(user, 'dealer')
        return dealer

class VerifyDealerSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField()

    class Meta:
        model = Dealer
        fields = ['is_verified']

    def validate_is_verified(self, value):
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify dealers.")
        return value
