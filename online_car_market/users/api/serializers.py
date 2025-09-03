from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import LoginSerializer
from rolepermissions.checkers import has_role
from rolepermissions.roles import get_user_roles, assign_role, remove_role
from django.contrib.auth import get_user_model
from online_car_market.users.models import Profile
from online_car_market.buyers.models import BuyerProfile, LoyaltyProgram
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
import cloudinary.uploader
import re
import bleach
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

class LoyaltyProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyProgram
        fields = ['id', 'points', 'reward', 'created_at']
        read_only_fields = ['id', 'points', 'reward', 'created_at']

class BuyerProfileSerializer(serializers.ModelSerializer):
    loyalty_programs = LoyaltyProgramSerializer(many=True, read_only=True)

    class Meta:
        model = BuyerProfile
        fields = ['loyalty_points', 'loyalty_programs']
        read_only_fields = ['loyalty_points', 'loyalty_programs']

class DealerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ['company_name', 'license_number', 'tax_id', 'telebirr_account', 'is_verified']
        read_only_fields = ['is_verified']

    def validate_company_name(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned) > 255:
            raise serializers.ValidationError("Company name cannot exceed 255 characters.")
        return cleaned

    def validate_license_number(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned) > 50:
            raise serializers.ValidationError("License number cannot exceed 50 characters.")
        return cleaned

    def validate_tax_id(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 100:
                raise serializers.ValidationError("Tax ID cannot exceed 100 characters.")
            return cleaned
        return value

    def validate_telebirr_account(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 100:
                raise serializers.ValidationError("Telebirr account cannot exceed 100 characters.")
            return cleaned
        return value

class BrokerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerProfile
        fields = ['national_id', 'telebirr_account', 'is_verified']
        read_only_fields = ['is_verified']

    def validate_national_id(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned) > 100:
            raise serializers.ValidationError("National ID cannot exceed 100 characters.")
        if BrokerProfile.objects.filter(national_id=cleaned).exclude(profile=self.instance.profile if self.instance else None).exists():
            raise serializers.ValidationError("This national ID is already in use.")
        return cleaned

    def validate_telebirr_account(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned) > 100:
            raise serializers.ValidationError("Telebirr account cannot exceed 100 characters.")
        return cleaned

class VerifyBrokerSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField()

    class Meta:
        model = BrokerProfile
        fields = ['is_verified']

    def validate_is_verified(self, value):
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify brokers.")
        return value

class VerifyDealerSerializer(serializers.ModelSerializer):
    is_verified = serializers.BooleanField()

    class Meta:
        model = DealerProfile
        fields = ['is_verified']

    def validate_is_verified(self, value):
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify dealers.")
        return value


class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault())
    buyer_profile = BuyerProfileSerializer(read_only=True)
    dealer_profile = DealerProfileSerializer(required=False, allow_null=True)
    broker_profile = BrokerProfileSerializer(required=False, allow_null=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Profile
        fields = ['id', 'user', 'first_name', 'last_name', 'contact', 'address', 'image', 'created_at', 'updated_at', 'buyer_profile', 'dealer_profile', 'broker_profile']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'buyer_profile']

    def validate_first_name(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 50:
                raise serializers.ValidationError("First name cannot exceed 50 characters.")
            return cleaned
        return value

    def validate_last_name(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 50:
                raise serializers.ValidationError("Last name cannot exceed 50 characters.")
            return cleaned
        return value

    def validate_contact(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 20:
                raise serializers.ValidationError("Contact cannot exceed 20 characters.")
            if not re.match(r'^\+?[\d\s-]{7,20}$', cleaned):
                raise serializers.ValidationError("Invalid contact number format.")
            return cleaned
        return value

    def validate_address(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 500:
                raise serializers.ValidationError("Address cannot exceed 500 characters.")
            return cleaned
        return value

    def validate_image(self, value):
        if value:
            # Validate image size (e.g., max 5MB)
            max_size = 5 * 1024 * 1024  # 5MB in bytes
            if value.size > max_size:
                raise serializers.ValidationError("Image size cannot exceed 5MB.")
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("Image must be JPEG, PNG, or GIF.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        if self.instance and self.instance.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("You can only update your own profile.")
        if data.get('dealer_profile') and not has_role(user, 'dealer'):
            raise serializers.ValidationError("Only dealers can update dealer profile fields.")
        if data.get('broker_profile') and not has_role(user, 'broker'):
            raise serializers.ValidationError("Only brokers can update broker profile fields.")
        return data

    def update(self, instance, validated_data):
        dealer_profile_data = validated_data.pop('dealer_profile', None)
        broker_profile_data = validated_data.pop('broker_profile', None)
        image = validated_data.pop('image', None)

        # Update Profile fields
        instance = super().update(instance, validated_data)

        # Handle image upload to Cloudinary
        if image:
            try:
                upload_result = cloudinary.uploader.upload(
                    image,
                    folder='profiles',
                    resource_type='image',
                    overwrite=True
                )
                instance.image = upload_result['public_id']
                instance.save()
                logger.info(f"Profile image uploaded for {instance.user.email}: {upload_result['public_id']}")
            except Exception as e:
                logger.error(f"Failed to upload profile image for {instance.user.email}: {str(e)}")
                raise serializers.ValidationError({"image": "Failed to upload image to Cloudinary."})

        # Update DealerProfile if applicable
        if dealer_profile_data and has_role(instance.user, 'dealer'):
            dealer_profile, _ = DealerProfile.objects.get_or_create(profile=instance)
            DealerProfileSerializer().update(dealer_profile, dealer_profile_data)

        # Update BrokerProfile if applicable
        if broker_profile_data and has_role(instance.user, 'broker'):
            broker_profile, _ = BrokerProfile.objects.get_or_create(profile=instance)
            BrokerProfileSerializer().update(broker_profile, broker_profile_data)

        return instance

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password', 'description']
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate_email(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if User.objects.filter(email=cleaned).exists():
            raise serializers.ValidationError("This email is already in use.")
        return cleaned

    def validate_password(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if not any(char.isupper() for char in cleaned):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not any(char.isdigit() for char in cleaned):
            raise serializers.ValidationError("Password must contain at least one digit.")
        return cleaned

    def validate_description(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 500:
                raise serializers.ValidationError("Description cannot exceed 500 characters.")
            return cleaned
        return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        Profile.objects.get_or_create(user=user)
        if not has_role(user, ['dealer', 'broker', 'admin', 'super_admin']):
            assign_role(user, 'Buyer')
            BuyerProfile.objects.get_or_create(profile=Profile.objects.get(user=user))
        logger.info(f"User created: {user.email}")
        return user

class UserRoleSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    role = serializers.ChoiceField(choices=[
        ('Buyer', 'Buyer'),
        ('Dealer', 'Dealer'),
        ('Broker', 'Broker'),
        ('Admin', 'Admin'),
        ('SuperAdmin', 'SuperAdmin'),
    ])

    def validate(self, data):
        user = self.context['request'].user
        target_user = data.get('user_id')
        role = data.get('role')

        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can assign roles.")
        if target_user == user and role != 'Admin':
            raise serializers.ValidationError("You cannot change your own role unless assigning Admin.")
        return data

    def save(self):
        user = self.validated_data['user_id']
        role = self.validated_data['role']
        current_roles = [role.get_name() for role in get_user_roles(user)]
        for current_role in current_roles:
            remove_role(user, current_role)
        assign_role(user, role)
        if role == 'Buyer':
            Profile.objects.get_or_create(user=user)
            BuyerProfile.objects.get_or_create(profile=Profile.objects.get(user=user))
        elif role == 'Dealer':
            Profile.objects.get_or_create(user=user)
            DealerProfile.objects.get_or_create(profile=Profile.objects.get(user=user), defaults={'company_name': user.email, 'license_number': '', 'telebirr_account': ''})
        elif role == 'Broker':
            Profile.objects.get_or_create(user=user)
            BrokerProfile.objects.get_or_create(profile=Profile.objects.get(user=user), defaults={'national_id': f"ID_{user.id}", 'telebirr_account': ''})
        logger.info(f"Role assigned to {user.email}: {role}")
        return user

class CustomLoginSerializer(LoginSerializer):
    username = None
    email = serializers.EmailField(required=True)

    def validate(self, attrs):
        return super().validate(attrs)

class CustomRegisterSerializer(RegisterSerializer):
    username = None
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)

    @property
    def _has_phone_field(self):
        return False

    def validate_email(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, cleaned):
            raise serializers.ValidationError("Email must be a valid email address.")
        if len(cleaned) > 254:
            raise serializers.ValidationError("Email cannot exceed 254 characters.")
        if User.objects.filter(email=cleaned).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return cleaned

    def validate_description(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 500:
                raise serializers.ValidationError("Description cannot exceed 500 characters.")
            return cleaned
        return value

    def validate(self, data):
        user = self.context['request'].user
        if user.is_authenticated and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can create users via this endpoint.")
        return data

    def save(self, request):
        user = super().save(request)
        assign_role(user, 'buyer')
        Profile.objects.get_or_create(user=user)
        BuyerProfile.objects.get_or_create(profile=Profile.objects.get(user=user))
        logger.info(f"User registered via dj_rest_auth: {user.email}")
        return user
