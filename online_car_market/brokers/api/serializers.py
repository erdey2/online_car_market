from rest_framework import serializers
from online_car_market.brokers.models import Broker
from online_car_market.inventory.api.serializers import CarSerializer
from online_car_market.brokers.models import BrokerListing

class BrokerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Broker
        fields = ['id', 'name', 'contact', 'commission_rate']

class BrokerListingSerializer(serializers.ModelSerializer):
    broker = BrokerSerializer(read_only=True)
    car = CarSerializer(read_only=True)
    class Meta:
        model = BrokerListing
        fields = ['id', 'broker', 'car', 'commission', 'created_at']
