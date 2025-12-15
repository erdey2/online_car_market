from rest_framework import serializers
from ..models import Bid
from online_car_market.inventory.models import Car
from online_car_market.users.models import Profile
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'contact']

class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['make', 'model']

class BidSerializer(serializers.ModelSerializer):
    # user = serializers.PrimaryKeyRelatedField(read_only=True)
    profile = ProfileSerializer(source='user.profile', read_only=True)
    car = CarSerializer(source='car', read_only=True)
    #first_name = serializers.CharField(source="user.profile.first_name", read_only=True)
    #last_name = serializers.CharField(source="user.profile.last_name", read_only=True)
    #contact = serializers.CharField(source="user.profile.contact", read_only=True)
    #make = serializers.CharField(source="car.make", read_only=True)
    #model = serializers.CharField(source="car.model", read_only=True)

    class Meta:
        model = Bid
        fields = ['id','car', 'user','profile', 'amount','created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def validate_car(self, value):
        # Ensure the car exists and is available for bidding
        if not value.status:
            raise serializers.ValidationError("This car is not available for bidding.")
        return value

    def validate_amount(self, value):
        # Ensure amount is positive
        if value <= 0:
            raise serializers.ValidationError("Bid amount must be greater than zero.")
        return value

    def create(self, validated_data):
        # Automatically set the user to the authenticated user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

