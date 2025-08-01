from rest_framework import serializers
from online_car_market.users.api.serializers import UserSerializer
from online_car_market.inventory.api.serializers import CarSerializer
from online_car_market.buyers.models import Buyer, Rating, LoyaltyProgram, Dealer


class BuyerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Buyer
        fields = ['id', 'user', 'contact', 'loyalty_points']

class DealerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Dealer
        fields = ['name', 'license_number', 'address', 'created_at', 'updated_at']

class RatingSerializer(serializers.ModelSerializer):
    buyer = UserSerializer(read_only=True)
    car = CarSerializer(read_only=True)
    class Meta:
        model = Rating
        fields = ['id', 'buyer', 'car', 'rating', 'comment', 'created_at']

class LoyaltyProgramSerializer(serializers.ModelSerializer):
    buyer = BuyerSerializer(read_only=True)
    class Meta:
        model = LoyaltyProgram
        fields = ['id', 'buyer', 'points', 'reward', 'created_at']
