from rest_framework import serializers
from rolepermissions.checkers import has_role
from online_car_market.users.api.serializers import UserSerializer
from online_car_market.inventory.api.serializers import CarSerializer
from online_car_market.buyers.models import Buyer, Rating, LoyaltyProgram, Dealer
import re


class BuyerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Buyer
        fields = ['id', 'user', 'contact', 'address', 'loyalty_points', 'loyalty_created_at', 'updated_at']
        read_only_fields = ['id', 'loyalty_created_at', 'updated_at']

    def validate_contact(self, value):
        """Ensure contact is a valid phone number."""
        if not re.match(r'^\+251[79]\d{8}$', value):
            raise serializers.ValidationError("Contact must be a valid phone number (e.g., +251912345678).")
        return value

    def validate_address(self, value):
        """Ensure address is valid and within length."""
        if value and len(value) > 100:
            raise serializers.ValidationError("Address cannot exceed 100 characters.")
        return value

    def validate_loyalty_points(self, value):
        """Ensure loyalty_points is non-negative and reasonable."""
        if value < 0:
            raise serializers.ValidationError("Loyalty points cannot be negative.")
        if value > 100000:
            raise serializers.ValidationError("Loyalty points cannot exceed 100,000.")
        return value

    def validate(self, data):
        """Ensure user has buyer role."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'buyer']):
            raise serializers.ValidationError("Only buyers, admins, or super admins can create buyer profiles.")
        if self.instance and self.instance.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the profile owner or admins can update this profile.")
        return data


class DealerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Dealer
        fields = ['id', 'user', 'name', 'license_number', 'address', 'telebirr_account', 'created_at', 'updated_at']
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

    def validate_license_number(self, value):
        """Ensure license_number is unique and alphanumeric."""
        if not re.match(r'^[A-Za-z0-9-]+$', value):
            raise serializers.ValidationError("License number must be alphanumeric with hyphens.")
        if len(value) > 50:
            raise serializers.ValidationError("License number cannot exceed 50 characters.")
        if self.instance is None and Dealer.objects.filter(license_number=value).exists():
            raise serializers.ValidationError("A dealer with this license number already exists.")
        return value

    def validate_address(self, value):
        """Ensure address is valid."""
        if len(value) > 100:
            raise serializers.ValidationError("Address cannot exceed 100 characters.")
        return value

    def validate_telebirr_account(self, value):
        """Ensure telebirr_account is a valid Ethiopian phone number."""
        if value and not re.match(r'^\+251[79]\d{8}$', value):
            raise serializers.ValidationError(
                "Telebirr account must be a valid Ethiopian phone number (e.g., +251912345678).")
        return value

    def validate(self, data):
        """Ensure user has dealer role."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'dealer']):
            raise serializers.ValidationError("Only dealers, admins, or super admins can create dealer profiles.")
        if self.instance and self.instance.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the profile owner or admins can update this profile.")
        return data

class RatingSerializer(serializers.ModelSerializer):
    buyer = UserSerializer(read_only=True)
    car = CarSerializer(read_only=True)

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
        """Ensure comment is within length."""
        if value and len(value) > 1000:
            raise serializers.ValidationError("Comment cannot exceed 1000 characters.")
        return value

    def validate(self, data):
        """Ensure only buyers can create ratings and user matches buyer role."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, 'buyer'):
            raise serializers.ValidationError("Only buyers can create ratings.")
        if self.instance and self.instance.buyer != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the rating owner or admins can update this rating.")
        return data

class LoyaltyProgramSerializer(serializers.ModelSerializer):
    buyer = BuyerSerializer(read_only=True)

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
        """Ensure reward is within length."""
        if value and len(value) > 100:
            raise serializers.ValidationError("Reward cannot exceed 100 characters.")
        return value

    def validate(self, data):
        """Ensure only admins or super admins can create/update loyalty programs."""
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only admins or super admins can manage loyalty programs.")
        return data
