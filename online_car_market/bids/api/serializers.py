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
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), write_only=True )
    # READ
    car_detail = CarSerializer(source='car', read_only=True)
    profile = ProfileSerializer(source='user.profile', read_only=True)

    class Meta:
        model = Bid
        fields = [
            'id',
            'car',          # for create/update
            'car_detail',   # for response
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


