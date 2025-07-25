from rest_framework import serializers
from online_car_market.inventory.api.serializers import CarSerializer
from online_car_market.users.api.serializers import UserSerializer
from online_car_market.sales.models import Sale, Expense, Lead
from online_car_market.brokers.models import Broker


class SaleSerializer(serializers.ModelSerializer):
    car = CarSerializer(read_only=True)
    buyer = UserSerializer(read_only=True)
    broker = serializers.PrimaryKeyRelatedField(queryset=Broker.objects.all(), allow_null=True)

    class Meta:
        model = Sale
        fields = ['id', 'car', 'buyer', 'price', 'date', 'broker']

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['id', 'type', 'amount', 'date', 'description']

class LeadSerializer(serializers.ModelSerializer):
    assigned_sales = UserSerializer(read_only=True)
    class Meta:
        model = Lead
        fields = ['id', 'name', 'contact', 'status', 'assigned_sales', 'created_at']

