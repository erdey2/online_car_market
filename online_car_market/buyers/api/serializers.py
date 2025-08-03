from rest_framework import serializers
from rolepermissions.checkers import has_role
from online_car_market.users.api.serializers import UserSerializer
from online_car_market.inventory.api.serializers import CarSerializer
from online_car_market.buyers.models import Buyer, Rating, LoyaltyProgram, Dealer
import re, bleach


class BuyerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Buyer
        fields = ['id', 'user', 'contact', 'address', 'loyalty_points', 'loyalty_created_at', 'updated_at']
        read_only_fields = ['id', 'loyalty_created_at', 'updated_at']

    def validate_contact(self, value):
        """Validate and sanitize phone number."""
        if not value:
            raise serializers.ValidationError("Contact is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        phone_regex = r'^\+251[79]\d{8}$'
        if not (re.match(phone_regex, cleaned_value)):
            raise serializers.ValidationError(
                "Contact must be a valid phone number (e.g., +251912345678).")
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Contact cannot exceed 100 characters.")
        return cleaned_value

    def validate_address(self, value):
        """Sanitize and validate address."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 100:
                raise serializers.ValidationError("Address cannot exceed 100 characters.")
            return cleaned_value
        return value

    def validate_loyalty_points(self, value):
        """Validate loyalty points."""
        if value < 0:
            raise serializers.ValidationError("Loyalty points cannot be negative.")
        if value > 1000000:
            raise serializers.ValidationError("Loyalty points cannot exceed 1,000,000.")
        return value

    def validate_user(self, value):
        """Ensure user has buyer role."""
        user = value.get('id') or (self.instance.user if self.instance else None)
        if user and not has_role(user, 'buyer'):
            raise serializers.ValidationError("The assigned user must have the buyer role.")
        return value

    def validate(self, data):
        """Ensure only super_admin, admin, or the buyer can manage their profile."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'buyer']):
            raise serializers.ValidationError("Only super admins, admins, or buyers can create buyer profiles.")
        if self.instance and self.instance.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins, admins, or the buyer can update this profile.")
        return data


class DealerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    # user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Dealer
        fields = ['id', 'user', 'name', 'license_number', 'address', 'telebirr_account', 'created_at', 'updated_at']
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

class RatingSerializer(serializers.ModelSerializer):
    buyer = UserSerializer(read_only=True)
    car = CarSerializer(read_only=True)
    # buyer = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    # car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())

    class Meta:
        model = Rating
        fields = ['id', 'buyer', 'car', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'buyer', 'created_at']

    def validate_rating(self, value):
        """Ensure rating is between 1 and 5."""
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_comment(self, value):
        """Sanitize and validate comment."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 1000:
                raise serializers.ValidationError("Comment cannot exceed 1000 characters.")
            return cleaned_value
        return value

    def validate_buyer(self, value):
        """Ensure buyer has buyer role."""
        if not has_role(value, 'buyer'):
            raise serializers.ValidationError("The assigned user must have the buyer role.")
        return value

    def validate(self, data):
        """Ensure only super_admin, admin, or the buyer can manage their ratings."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'buyer']):
            raise serializers.ValidationError("Only super admins, admins, or buyers can create ratings.")
        if self.instance and self.instance.buyer != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins, admins, or the buyer can update this rating.")
        return data

class LoyaltyProgramSerializer(serializers.ModelSerializer):
    buyer = BuyerSerializer(read_only=True)
    # buyer = serializers.PrimaryKeyRelatedField(queryset=Buyer.objects.all())

    class Meta:
        model = LoyaltyProgram
        fields = ['id', 'buyer', 'points', 'reward', 'created_at']
        read_only_fields = ['id', 'buyer', 'created_at']

    def validate_points(self, value):
        """Ensure points is non-negative and reasonable."""
        if value < 0:
            raise serializers.ValidationError("Points cannot be negative.")
        if value > 100000:
            raise serializers.ValidationError("Points cannot exceed 100,000.")
        return value

    def validate_reward(self, value):
        """Sanitize and validate reward."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 100:
                raise serializers.ValidationError("Reward cannot exceed 100 characters.")
            return cleaned_value
        return value

    def validate(self, data):
        """Ensure only admins or super admins can create/update loyalty programs."""
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only admins or super admins can manage loyalty programs.")
        return data
