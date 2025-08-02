from rest_framework import serializers
from rolepermissions.checkers import has_role
from ..models import Car, CarImage
from online_car_market.buyers.models import Dealer
from online_car_market.users.api.serializers import UserSerializer
import re
from datetime import datetime

class CarImageSerializer(serializers.ModelSerializer):
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())
    image = serializers.CharField()  # CloudinaryField treated as CharField for validation

    class Meta:
        model = CarImage
        fields = ['id', 'car', 'image', 'is_featured', 'caption', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def validate_image(self, value):
        """Ensure image is a valid Cloudinary reference."""
        if not value:
            raise serializers.ValidationError("Image is required.")
        # Basic validation for Cloudinary public_id or URL
        if not re.match(r'^[a-zA-Z0-9_-]+(/[a-zA-Z0-9_-]+)*$', value) and not value.startswith('http'):
            raise serializers.ValidationError("Invalid Cloudinary image reference or URL.")
        return value

    def validate_caption(self, value):
        """Ensure caption is within length."""
        if value and len(value) > 255:
            raise serializers.ValidationError("Caption cannot exceed 255 characters.")
        return value

    def validate_is_featured(self, value):
        """Ensure only one image per car is featured."""
        if value and self.instance and self.instance.is_featured:
            # Allow updating existing featured image
            return value
        if value:
            car = self.initial_data.get('car') or (self.instance.car.pk if self.instance else None)
            if car and CarImage.objects.filter(car_id=car, is_featured=True).exists():
                raise serializers.ValidationError("Another image is already featured for this car.")
        return value

    def validate(self, data):
        """Ensure only dealers or admins can manage images."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'dealer']):
            raise serializers.ValidationError("Only dealers, admins, or super admins can create car images.")
        if self.instance and data.get('car') and data['car'].dealer and data['car'].dealer.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the dealer owner or admins can update this car image.")
        return data

class CarSerializer(serializers.ModelSerializer):
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all(), required=False, allow_null=True)
    images = CarImageSerializer(many=True, read_only=True)

    class Meta:
        model = Car
        fields = ['id', 'make', 'model', 'year', 'price', 'mileage', 'fuel_type', 'status', 'dealer', 'created_at', 'updated_at', 'images']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_make(self, value):
        """Ensure make is valid."""
        if not value:
            raise serializers.ValidationError("Make is required.")
        if len(value) > 100:
            raise serializers.ValidationError("Make cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', value):
            raise serializers.ValidationError("Make can only contain letters, numbers, spaces, or hyphens.")
        return value

    def validate_model(self, value):
        """Ensure model is valid."""
        if not value:
            raise serializers.ValidationError("Model is required.")
        if len(value) > 100:
            raise serializers.ValidationError("Model cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', value):
            raise serializers.ValidationError("Model can only contain letters, numbers, spaces, or hyphens.")
        return value

    def validate_year(self, value):
        """Ensure year is valid."""
        current_year = datetime.now().year
        if not 1900 <= value <= current_year + 1:
            raise serializers.ValidationError(f"Year must be between 1900 and {current_year + 1}.")
        return value

    def validate_price(self, value):
        """Ensure price is non-negative and reasonable."""
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        if value > 100000000:  # Max 100 million
            raise serializers.ValidationError("Price cannot exceed 100,000,000.")
        return value

    def validate_mileage(self, value):
        """Ensure mileage is non-negative."""
        if value < 0:
            raise serializers.ValidationError("Mileage cannot be negative.")
        if value > 1000000:  # Max 1 million km
            raise serializers.ValidationError("Mileage cannot exceed 1,000,000 km.")
        return value

    def validate_fuel_type(self, value):
        """Ensure fuel_type is valid."""
        valid_types = ['electric', 'hybrid', 'petrol', 'diesel']
        if value not in valid_types:
            raise serializers.ValidationError(f"Fuel type must be one of: {', '.join(valid_types)}.")
        return value

    def validate_status(self, value):
        """Ensure status is valid."""
        valid_statuses = ['available', 'reserved', 'sold', 'pending_inspection', 'under_maintenance', 'delivered', 'archived']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(valid_statuses)}.")
        return value

    def validate_dealer(self, value):
        """Ensure dealer has dealer role."""
        if value and not has_role(value.user, 'dealer'):
            raise serializers.ValidationError("The assigned user must have the dealer role.")
        return value

    def validate(self, data):
        """Ensure only dealers or admins can create/update cars."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'dealer']):
            raise serializers.ValidationError("Only dealers, admins, or super admins can create cars.")
        if self.instance and data.get('dealer') and data['dealer'].user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the dealer owner or admins can update this car.")
        return data
