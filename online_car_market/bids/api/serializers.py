from rest_framework import serializers
from ..models import Bid
from online_car_market.inventory.models import Car
from online_car_market.users.models import Profile
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'first_name', 'last_name', 'contact']

class CarMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['id', 'make', 'model']

class BidSerializer(serializers.ModelSerializer):
    # WRITE
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), write_only=True)

    # READ
    car_detail = CarMiniSerializer(source='car', read_only=True)
    profile = ProfileMiniSerializer(source='user.profile', read_only=True)

    class Meta:
        model = Bid
        fields = [
            'id',
            'car',
            'car_detail',
            'profile',
            'amount',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_car(self, car):
        if not car.status:
            raise serializers.ValidationError(
                "This car is not available for bidding."
            )
        return car

    def validate_amount(self, amount):
        if amount <= 0:
            raise serializers.ValidationError(
                "Bid amount must be greater than zero."
            )
        return amount

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
