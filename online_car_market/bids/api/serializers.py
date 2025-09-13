from rest_framework import serializers
from ..models import Bid
from online_car_market.inventory.models import Car
from django.contrib.auth import get_user_model

User = get_user_model()

class BidSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Bid
        fields = ['id', 'car', 'user', 'amount', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def validate_car(self, value):
        # Ensure the car exists and is available for bidding
        if not value.is_available:
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

