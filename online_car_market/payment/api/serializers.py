from rest_framework import serializers
from ..models import Payment
from online_car_market.brokers.models import BrokerProfile
from online_car_market.inventory.models import Car
from django.contrib.auth import get_user_model
from rolepermissions.checkers import has_role

User = get_user_model()

class PaymentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault())
    broker = serializers.PrimaryKeyRelatedField(queryset=BrokerProfile.objects.all(), required=False, allow_null=True)
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Payment
        fields = ['id', 'user', 'broker', 'car', 'amount', 'payment_date', 'status', 'transaction_id']
        read_only_fields = ['id', 'payment_date']

    def validate(self, data):
        user = data.get('user') or self.context['request'].user
        if data.get('broker') and not has_role(user, 'broker'):
            raise serializers.ValidationError("Only brokers can be associated with broker payments.")
        if data.get('car') and data.get('broker') and data['car'].broker != data['broker']:
            raise serializers.ValidationError("Car must belong to the specified broker.")
        if data.get('amount', 0) <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return data
