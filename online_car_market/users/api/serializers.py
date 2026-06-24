import re, bleach, logging, cloudinary, cloudinary.uploader
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import LoginSerializer
from rolepermissions.checkers import has_role
from rolepermissions.roles import get_user_roles, assign_role
from rolepermissions.exceptions import RoleDoesNotExist
from django.contrib.auth import get_user_model
from online_car_market.users.models import Profile
from online_car_market.buyers.models import BuyerProfile
from online_car_market.brokers.api.serializers import BrokerProfileSerializer
from online_car_market.dealers.api.serializers import DealerProfileSerializer
from online_car_market.buyers.api.serializers import BuyerProfileSerializer
from ..services.user_service import UserService
from ..services.profile_service import ProfileService
from online_car_market.brokers.models import BrokerProfile
from online_car_market.dealers.models import DealerProfile

logger = logging.getLogger(__name__)
User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    contact = serializers.CharField(max_length=20, required=False, allow_blank=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password', 'first_name', 'last_name', 'contact','description']
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

    def validate_contact(self, value):
        if value:
            value = bleach.clean(
                value.strip(),
                tags=[],
                strip=True
            )

            if len(value) > 15:
                raise serializers.ValidationError(
                    "Contact cannot exceed 15 characters."
                )

        return value

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
        return UserService.register_user(validated_data)

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
        ('super_admin', 'SuperAdmin'),
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

    def create(self, validated_data):
        user = validated_data['user_id']
        role = validated_data['role']
        return UserService.assign_role_to_user(user, role)

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
    dealer_profile = DealerProfileSerializer(read_only=True)
    broker_profile = BrokerProfileSerializer(read_only=True)

    image = serializers.ImageField(required=False, allow_null=True)
    image_url = serializers.SerializerMethodField(read_only=True)
    role = serializers.SerializerMethodField(read_only=True)

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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        role = instance.user.role

        if role != "dealer":
            data.pop("dealer_profile", None)
        if role != "broker":
            data.pop("broker_profile", None)
        if role != "buyer":
            data.pop("buyer_profile", None)

        return data

    @extend_schema_field(serializers.CharField())
    def get_role(self, obj) -> str:
        return obj.user.role if obj.user else None

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
        logger.info(f"Updating profile for user_id={request.user.id}")

        dealer_profile_data = validated_data.pop('dealer_profile', None)
        broker_profile_data = validated_data.pop('broker_profile', None)
        image = validated_data.pop('image', None)

        instance = super().update(instance, validated_data)

        if image:
            instance.image = ProfileService.upload_profile_image(image)
            instance.save()

        ProfileService.update_related_profiles(
            instance,
            dealer_profile_data,
            broker_profile_data
        )

        return instance

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'date_joined', 'is_active']

class ERPLoginSerializer(LoginSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)
        user = data.get("user")

        roles = get_user_roles(user)
        logger.info(f"User roles: {roles}")

        if not user:
            raise serializers.ValidationError("Authentication failed.")

        # Allow only ERP roles
        allowed_roles = ["dealer", "hr", "seller", "accountant", "finance"]

        if not any(has_role(user, role) for role in allowed_roles):
            raise serializers.ValidationError(
                "You are not allowed to access the ERP system."
            )

        return data

class AdminLoginSerializer(LoginSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = data.get("user")

        # Allow admin OR superadmin
        if not has_role(user, ["admin", "super_admin"]):
            raise serializers.ValidationError(
                "You are not allowed to access the Admin system."
            )

        return data

class BuyerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            role=User.Role.BUYER
        )

        Profile.objects.create(user=user)
        return user

class BrokerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    national_id = serializers.CharField()
    telebirr_account = serializers.CharField()

    class Meta:
        model = User
        fields = ["email", "password", "national_id", "telebirr_account"]

    def create(self, validated_data):
        national_id = validated_data.pop("national_id")
        telebirr = validated_data.pop("telebirr_account")

        user = User.objects.create_user(
            role=User.Role.BUYER,  # STILL buyer until approved
            **validated_data
        )

        profile = Profile.objects.create(user=user)

        BrokerProfile.objects.create(
            profile=profile,
            national_id=national_id,
            telebirr_account=telebirr,
            status=BrokerProfile.Status.PENDING
        )

        return user

class DealerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    company_name = serializers.CharField()
    license_number = serializers.CharField()
    tax_id = serializers.CharField(required=False)
    telebirr_account = serializers.CharField(required=False)
    business_license = serializers.FileField(required=True)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "company_name",
            "license_number",
            "tax_id",
            "telebirr_account",
            "business_license",
        ]

    def create(self, validated_data):
        company_name = validated_data.pop("company_name")
        license_number = validated_data.pop("license_number")
        tax_id = validated_data.pop("tax_id", None)
        telebirr = validated_data.pop("telebirr_account", None)
        business_license = validated_data.pop("business_license", None)

        user = User.objects.create_user(
            role=User.Role.BUYER,
            **validated_data
        )

        profile = Profile.objects.create(user=user)

        DealerProfile.objects.create(
            profile=profile,
            company_name=company_name,
            license_number=license_number,
            tax_id=tax_id,
            telebirr_account=telebirr,
            business_license=business_license,
            status=DealerProfile.Status.PENDING
        )

        return user

class DealerProfileSerializer2(serializers.ModelSerializer):
    class Meta:
        model = DealerProfile
        fields = ['id', 'company_name', 'license_number', 'tax_id', 'telebirr_account', 'status', 'is_verified']

class BrokerProfileSerializer2(serializers.ModelSerializer):
    class Meta:
        model = BrokerProfile
        fields = ['id', 'national_id', 'telebirr_account', 'status', 'is_verified']

class ProfileSerializer2(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'first_name', 'last_name', 'contact', 'address', 'image']

class UserFullSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'role', 'date_joined', 'profile']

    def get_profile(self, obj):
        if not hasattr(obj, 'profile'):
            return None

        profile_data = ProfileSerializer(obj.profile).data

        # Include only the relevant role profile, flattening nested profile
        if obj.role == User.Role.DEALER and hasattr(obj.profile, 'dealer_profile'):
            dealer = obj.profile.dealer_profile
            dealer_data = DealerProfileSerializer(dealer).data

            dealer_data.pop('profile', None)
            profile_data['dealer_profile'] = dealer_data
        elif obj.role == User.Role.BROKER and hasattr(obj.profile, 'broker_profile'):
            broker = obj.profile.broker_profile
            broker_data = BrokerProfileSerializer(broker).data
            broker_data.pop('profile', None)
            profile_data['broker_profile'] = broker_data

        return profile_data





