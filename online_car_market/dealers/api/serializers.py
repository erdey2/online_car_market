from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from rolepermissions.checkers import has_role
from online_car_market.common.serializers import ProfileLiteSerializer
from online_car_market.users.models import User
from ..models import DealerProfile, DealerStaff, DealerRating
import bleach
import logging

logger = logging.getLogger(__name__)

class DealerProfileSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    profile = ProfileLiteSerializer(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    role = serializers.SerializerMethodField(read_only=True)
    business_license = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField())
    def get_role(self, obj):
        return obj.profile.user.role if obj.profile and obj.profile.user else None

    @extend_schema_field(serializers.URLField())
    def get_business_license(self, obj):
        if obj.business_license:
            return obj.business_license.url
        return None

    class Meta:
        model = DealerProfile
        fields = [
            'id',
            'profile',
            'company_name',
            'license_number',
            'tax_id',
            'telebirr_account',
            'business_license',
            'status',
            'is_verified',
            'role',
            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'id',
            'profile',
            'is_verified'
        ]

    def validate_company_name(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)

        if len(cleaned) > 255:
            raise serializers.ValidationError(
                "Company name cannot exceed 255 characters."
            )

        return cleaned

    def validate_license_number(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)

        if len(cleaned) > 50:
            raise serializers.ValidationError(
                "License number cannot exceed 50 characters."
            )

        return cleaned

    def validate_tax_id(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)

            if len(cleaned) > 100:
                raise serializers.ValidationError(
                    "Tax ID cannot exceed 100 characters."
                )

            return cleaned

        return value

    def validate_telebirr_account(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)

            if len(cleaned) > 100:
                raise serializers.ValidationError(
                    "Telebirr account cannot exceed 100 characters."
                )

            return cleaned

        return value

class DealerStaffSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(write_only=True)  # Input email to find/create user
    user = serializers.SerializerMethodField(read_only=True)
    role = serializers.ChoiceField(choices=[('seller', 'Seller'), ('accountant', 'Accountant'), ('hr', 'HR'), ('finance', 'Finance')])

    class Meta:
        model = DealerStaff
        fields = ['id', 'user_email', 'user', 'role', 'assigned_at', 'updated_at']
        read_only_fields = ['id', 'assigned_at', 'updated_at']


    @extend_schema_field({
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string"},
            "first_name": {"type": "string"},
            "last_name": {"type": "string"}
        }
    })
    def get_user(self, obj):
        user = obj.user
        profile = getattr(user, "profile", None)

        return {
            "id": user.id,
            "email": user.email,
            "first_name": getattr(profile, "first_name", ""),
            "last_name": getattr(profile, "last_name", ""),
        }

    def validate_user_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")

        request_user = self.context["request"].user
        dealer = getattr(request_user.profile, "dealer_profile", None)

        if not dealer:
            raise serializers.ValidationError("Only dealers can assign staff.")

        if DealerStaff.objects.filter(dealer=dealer, user=user).exists():
            raise serializers.ValidationError("Already assigned to this dealer.")

        return user

    def create(self, validated_data):
        user = validated_data.pop("user_email")
        role = validated_data.pop("role")

        request_user = self.context["request"].user
        dealer = getattr(request_user.profile, "dealer_profile", None)

        if not dealer:
            raise serializers.ValidationError("Only dealers can assign staff.")

        staff = DealerStaff.objects.create(
            dealer=dealer,
            user=user,
            role=role
        )

        return staff

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

class VerifyDealerSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField()

    class Meta:
        model = DealerProfile
        fields = ['is_verified']

    def validate_is_verified(self, value):
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']) and not user.is_superuser:
            raise serializers.ValidationError("Only super admins or admins can verify dealers.")
        return value
