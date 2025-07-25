from rest_framework import serializers
from online_car_market.inventory.models import Car

class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['id', 'make', 'model', 'year', 'price', 'mileage', 'fuel_type', 'images', 'created_at', 'updated_at']
