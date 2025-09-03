from rest_framework import serializers
from rolepermissions.checkers import has_role
from online_car_market.brokers.models import BrokerRating, BrokerProfile
from online_car_market.users.models import User
import bleach
import logging

logger = logging.getLogger(__name__)

class BrokerRatingSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault())

    class Meta:
        model = BrokerRating
        fields = ['id', 'broker', 'user', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'broker', 'created_at', 'updated_at']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_comment(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 500:
                raise serializers.ValidationError("Comment cannot exceed 500 characters.")
            return cleaned
        return value

    def validate(self, data):
        user = self.context['request'].user
        broker_id = self.context['view'].kwargs.get('broker_pk')
        broker = BrokerProfile.objects.filter(pk=broker_id).first()
        if not broker:
            raise serializers.ValidationError({"broker": "Broker does not exist."})
        if has_role(user, 'broker') and broker.profile.user == user:
            raise serializers.ValidationError("You cannot rate your own broker profile.")
        if BrokerRating.objects.filter(broker=broker, user=user).exists():
            raise serializers.ValidationError("You have already rated this broker.")
        return data
