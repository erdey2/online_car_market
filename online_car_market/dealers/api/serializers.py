from rest_framework import serializers
from rolepermissions.checkers import has_role
from online_car_market.dealers.models import DealerProfile, DealerRating
from online_car_market.users.models import User
import bleach
import logging

logger = logging.getLogger(__name__)

class DealerRatingSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault())

    class Meta:
        model = DealerRating
        fields = ['id', 'dealer', 'user', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'dealer', 'user', 'created_at', 'updated_at']

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
        dealer_id = self.context['view'].kwargs.get('dealer_pk')
        dealer = DealerProfile.objects.filter(pk=dealer_id).first()
        if not dealer:
            raise serializers.ValidationError({"dealer": "Dealer does not exist."})
        if has_role(user, 'dealer') and dealer.profile.user == user:
            raise serializers.ValidationError("You cannot rate your own dealer profile.")
        if DealerRating.objects.filter(dealer=dealer, user=user).exists():
            raise serializers.ValidationError("You have already rated this dealer.")
        return data
