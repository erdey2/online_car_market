from rest_framework import serializers
from ..models import Payment
from online_car_market.brokers.models import BrokerProfile
from online_car_market.inventory.models import Car
from django.contrib.auth import get_user_model
from rolepermissions.checkers import has_role

User = get_user_model()

class PaymentSerializer(serializers.ModelSerializer):
    broker = serializers.PrimaryKeyRelatedField(queryset=BrokerProfile.objects.all(), required=False, allow_null=True)
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Payment
        fields = ['id', 'broker', 'car', 'amount', 'payment_date', 'status', 'transaction_id']
        read_only_fields = ['id', 'payment_date']

    def validate(self, data):
        user = self.context['request'].user
        if data.get('broker') and not has_role(user, 'broker'):
            raise serializers.ValidationError("Only brokers can be associated with broker payments.")
        if data.get('car') and data.get('broker') and data['car'].broker != data['broker']:
            raise serializers.ValidationError("Car must belong to the specified broker.")
        if data.get('amount', 0) <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return data
