from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import LoginSerializer
from rolepermissions.checkers import has_role
from rolepermissions.roles import get_user_roles, assign_role, remove_role
from rolepermissions.exceptions import RoleDoesNotExist
from django.contrib.auth import get_user_model
from online_car_market.users.models import Profile
from online_car_market.buyers.models import BuyerProfile
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.brokers.api.serializers import BrokerProfileSerializer
from online_car_market.dealers.api.serializers import DealerProfileSerializer
from online_car_market.buyers.api.serializers import BuyerProfileSerializer
import cloudinary.uploader
import re
import bleach
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=50, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password', 'first_name', 'last_name', 'description']
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
        # Extract names before creating the user
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        validated_data.pop('confirm_password')

        user = User.objects.create_user(**validated_data)

        # Create or update profile with names
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.first_name = first_name
        profile.last_name = last_name
        profile.save()

        # Assign default buyer role
        try:
            if not has_role(user, ['dealer', 'broker', 'admin', 'super_admin']):
                assign_role(user, 'buyer')
                BuyerProfile.objects.get_or_create(profile=profile)
            logger.info(f"User created: {user.email}")
        except RoleDoesNotExist:
            logger.error(f"Role buyer does not exist for {user.email}")
            raise serializers.ValidationError("Role buyer does not exist.")

        return user

class UserMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='profile.get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name']

class UserRoleSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    role = serializers.ChoiceField(choices=[
        ('buyer', 'Buyer'),
        ('dealer', 'Dealer'),
        ('broker', 'Broker'),
        ('admin', 'Admin'),
        ('superadmin', 'SuperAdmin'),
    ])

    def validate(self, data):
        user = self.context['request'].user
        target_user = data.get('user_id')
        role = data.get('role')

        if not has_role(user, ['super_admin', 'admin']) and not user.is_superuser:
            raise serializers.ValidationError("Only super admins or admins can assign roles.")
        if target_user == user and role != 'admin':
            raise serializers.ValidationError("You cannot change your own role unless assigning Admin.")
        if not target_user.is_active:
            raise serializers.ValidationError("Cannot assign role to inactive user.")
        return data

    def save(self):
        user = self.validated_data['user_id']
        role = self.validated_data['role']
        current_roles = [role.get_name() for role in get_user_roles(user)]

        for current_role in current_roles:
            try:
                remove_role(user, current_role)
                logger.info(f"Removed role {current_role} from user {user.email}")
            except RoleDoesNotExist:
                logger.warning(f"Role {current_role} does not exist for {user.email}")

        try:
            assign_role(user, role)
        except RoleDoesNotExist:
            logger.error(f"Role {role} does not exist for {user.email}")
            raise serializers.ValidationError(f"Role {role} does not exist.")

        Profile.objects.get_or_create(user=user)
        if role == 'buyer':
            BuyerProfile.objects.get_or_create(profile=Profile.objects.get(user=user))
        elif role == 'dealer':
            DealerProfile.objects.get_or_create(
                profile=Profile.objects.get(user=user),
                defaults={'company_name': user.email, 'license_number': '', 'telebirr_account': ''}
            )
        elif role == 'broker':
            BrokerProfile.objects.get_or_create(
                profile=Profile.objects.get(user=user),
                defaults={'national_id': f"ID_{user.id}", 'telebirr_account': ''}
            )
        logger.info(f"Assigned role {role} to user {user.email}")
        return user

class CustomLoginSerializer(LoginSerializer):
    username = None
    email = serializers.EmailField(required=True)

    def validate(self, attrs):
        return super().validate(attrs)

class CustomRegisterSerializer(RegisterSerializer):
    username = None
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=50, required=False, allow_blank=True)

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
        if user.is_authenticated and not has_role(user, ['super_admin', 'admin']) and not user.is_superuser:
            raise serializers.ValidationError("Only super admins or admins can create users via this endpoint.")
        return data

    def save(self, request):
        user = super().save(request)

        # Get or create profile
        profile, _ = Profile.objects.get_or_create(user=user)

        # Save names and description
        profile.first_name = self.validated_data.get('first_name', '')
        profile.last_name = self.validated_data.get('last_name', '')
        profile.save()

        # Assign default buyer role
        try:
            assign_role(user, 'buyer')
            BuyerProfile.objects.get_or_create(profile=profile)
        except RoleDoesNotExist:
            raise serializers.ValidationError("Role buyer does not exist.")

        return user

class ProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    buyer_profile = BuyerProfileSerializer(read_only=True)
    dealer_profile = DealerProfileSerializer(required=False)
    broker_profile = BrokerProfileSerializer(required=False)
    image = serializers.ImageField(required=False, allow_null=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    role = serializers.SerializerMethodField(read_only=True)

    @extend_schema_field(serializers.CharField())
    def get_role(self, obj) -> str:
        roles = get_user_roles(obj.user)
        return roles[0].get_name() if roles else None

    def get_dealer_profile(self, obj):
        dealer_profile = getattr(obj, "dealer_profile", None)
        if dealer_profile:
            return DealerProfileSerializer(dealer_profile).data
        return None

    def get_broker_profile(self, obj):
        broker_profile = getattr(obj, "broker_profile", None)
        if broker_profile:
            return BrokerProfileSerializer(broker_profile).data
        return None

    class Meta:
        model = Profile
        fields = [
            'id', 'user', 'first_name', 'last_name', 'contact', 'address', 'role',
            'image', 'image_url', 'created_at', 'updated_at',
            'buyer_profile', 'dealer_profile', 'broker_profile'
        ]
        read_only_fields = [
            'id', 'user', 'role', 'created_at', 'updated_at', 'buyer_profile', 'image_url'
        ]

    def get_image_url(self, obj):
        if obj.image:
            url, _ = cloudinary.utils.cloudinary_url(str(obj.image), resource_type="image")
            return url
        return None

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
            max_size = 5 * 1024 * 1024  # 5MB in bytes
            if value.size > max_size:
                raise serializers.ValidationError("Image size cannot exceed 5MB.")
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("Image must be JPEG, PNG, or GIF.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        if self.instance and self.instance.user != user and not has_role(user, ['super_admin', 'admin']) and not user.is_superuser:
            raise serializers.ValidationError("You can only update your own profile.")
        if data.get('dealer_profile') and not has_role(user, 'dealer'):
            raise serializers.ValidationError("Only dealers can update dealer profile fields.")
        if data.get('broker_profile') and not has_role(user, 'broker'):
            raise serializers.ValidationError("Only brokers can update broker profile fields.")
        return data

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user_id = request.user.id  # ID from token
        logger.info(f"Updating profile for user_id={user_id}")

        dealer_profile_data = validated_data.pop('dealer_profile', None)
        broker_profile_data = validated_data.pop('broker_profile', None)
        image = validated_data.pop('image', None)

        instance = super().update(instance, validated_data)

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
                logger.info(f"Profile image uploaded for user_id={user_id}: {upload_result['public_id']}")
            except Exception as e:
                logger.error(f"Failed to upload profile image for user_id={user_id}: {str(e)}")
                raise serializers.ValidationError({"image": "Failed to upload image to Cloudinary."})

        if dealer_profile_data and has_role(instance.user, 'dealer'):
            dealer_profile, _ = DealerProfile.objects.get_or_create(profile=instance)
            DealerProfileSerializer().update(dealer_profile, dealer_profile_data)

        if broker_profile_data and has_role(instance.user, 'broker'):
            broker_profile, _ = BrokerProfile.objects.get_or_create(profile=instance)
            BrokerProfileSerializer().update(broker_profile, broker_profile_data)

        return instance

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'date_joined', 'is_active']

