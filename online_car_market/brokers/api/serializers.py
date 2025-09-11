from rest_framework import serializers
from rolepermissions.checkers import has_role
from online_car_market.brokers.models import BrokerRating, BrokerProfile
from online_car_market.users.models import User
from online_car_market.common.serializers import ProfileLiteSerializer
from rolepermissions.checkers import get_user_roles
import bleach
import logging

logger = logging.getLogger(__name__)

class BrokerProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    profile = serializers.PrimaryKeyRelatedField(read_only=True)
    national_id = serializers.CharField()
    telebirr_account = serializers.CharField(allow_blank=True)
    is_verified = serializers.BooleanField(read_only=True)
    role = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = BrokerProfile
        fields = ['id', 'profile', 'national_id', 'telebirr_account', 'is_verified', 'role']
        read_only_fields = ['id', 'profile','is_verified', 'role']

    def get_role(self, obj):
        """Return the user's role name(s) from django-role-permissions."""
        roles = get_user_roles(obj.profile.user)  # obj.profile.user is the User instance
        if not roles:
            return None
        return [role.get_name() for role in roles]

    def validate_national_id(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned) > 100:
            raise serializers.ValidationError("National ID cannot exceed 100 characters.")
        if BrokerProfile.objects.filter(national_id=cleaned).exclude(
            profile=self.instance.profile if self.instance else None
        ).exists():
            raise serializers.ValidationError("This national ID is already in use.")
        return cleaned

    def validate_telebirr_account(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 100:
                raise serializers.ValidationError("Telebirr account cannot exceed 100 characters.")
            return cleaned
        return value

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

class VerifyBrokerSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField()

    class Meta:
        model = BrokerProfile
        fields = ['is_verified']

    def validate_is_verified(self, value):
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']) and not user.is_superuser:
            raise serializers.ValidationError("Only super admins or admins can verify brokers.")
        return value
