from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import LoginSerializer
from rolepermissions.checkers import has_role
from rolepermissions.roles import get_user_roles
from django.contrib.auth import get_user_model
import re
import bleach

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'description', 'is_active', 'is_staff', 'is_superuser', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def get_role(self, obj):
        roles = get_user_roles(obj)
        if roles:
            return roles[0].get_name()  # return only the first role
        return None

    def validate_email(self, value):
        """Validate and sanitize email."""
        if not value:
            raise serializers.ValidationError("Email is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, cleaned_value):
            raise serializers.ValidationError("Email must be a valid email address.")
        if len(cleaned_value) > 254:  # EmailField max_length
            raise serializers.ValidationError("Email cannot exceed 254 characters.")
        if self.instance is None and User.objects.filter(email=cleaned_value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if self.instance and self.instance.email != cleaned_value and User.objects.filter(email=cleaned_value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return cleaned_value

    def validate_first_name(self, value):
        """Sanitize and validate first name."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 50:
                raise serializers.ValidationError("First name cannot exceed 50 characters.")
            if not re.match(r'^[a-zA-Z\s-]+$', cleaned_value):
                raise serializers.ValidationError("First name can only contain letters, spaces, or hyphens.")
            return cleaned_value
        return value

    def validate_last_name(self, value):
        """Sanitize and validate last name."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 50:
                raise serializers.ValidationError("Last name cannot exceed 50 characters.")
            if not re.match(r'^[a-zA-Z\s-]+$', cleaned_value):
                raise serializers.ValidationError("Last name can only contain letters, spaces, or hyphens.")
            return cleaned_value
        return value

    def validate_description(self, value):
        """Sanitize and validate description."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 500:
                raise serializers.ValidationError("Description cannot exceed 500 characters.")
            return cleaned_value
        return value

    def validate_is_active(self, value):
        """Restrict is_active changes to super_admin or admin."""
        user = self.context['request'].user
        if self.instance and self.instance.is_active != value and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can modify is_active.")
        return value

    def validate_is_staff(self, value):
        """Restrict is_staff changes to super_admin or admin."""
        user = self.context['request'].user
        if self.instance and self.instance.is_staff != value and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can modify is_staff.")
        return value

    def validate_is_superuser(self, value):
        """Restrict is_superuser changes to super_admin."""
        user = self.context['request'].user
        if self.instance and self.instance.is_superuser != value and not has_role(user, 'super_admin'):
            raise serializers.ValidationError("Only super admins can modify is_superuser.")
        return value

    def validate(self, data):
        """Ensure only super_admin, admin, or the user can manage profiles."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can create new users.")
        if self.instance and self.instance != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins, admins, or the user can update this profile.")
        return data

class CustomLoginSerializer(LoginSerializer):
    username = None  # remove username completely
    email = serializers.EmailField(required=True)

    def validate(self, attrs):
        # Let dj-rest-auth handle the authentication with email + password
        return super().validate(attrs)

class CustomRegisterSerializer(RegisterSerializer):
    username = None
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    def validate_email(self, value):
        """Sanitize and validate email."""
        if not value:
            raise serializers.ValidationError("Email is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, cleaned_value):
            raise serializers.ValidationError("Email must be a valid email address.")
        if len(cleaned_value) > 254:
            raise serializers.ValidationError("Email cannot exceed 254 characters.")
        if User.objects.filter(email=cleaned_value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return cleaned_value

    def validate_first_name(self, value):
        """Sanitize and validate first name."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 50:
                raise serializers.ValidationError("First name cannot exceed 50 characters.")
            if not re.match(r'^[a-zA-Z\s-]+$', cleaned_value):
                raise serializers.ValidationError("First name can only contain letters, spaces, or hyphens.")
            return cleaned_value
        return value

    def validate_last_name(self, value):
        """Sanitize and validate last name."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 50:
                raise serializers.ValidationError("Last name cannot exceed 50 characters.")
            if not re.match(r'^[a-zA-Z\s-]+$', cleaned_value):
                raise serializers.ValidationError("Last name can only contain letters, spaces, or hyphens.")
            return cleaned_value
        return value

    def get_cleaned_data(self):
        """Include sanitized first_name and last_name in cleaned data."""
        cleaned_data = super().get_cleaned_data()
        cleaned_data['first_name'] = self.validated_data.get('first_name', '')
        cleaned_data['last_name'] = self.validated_data.get('last_name', '')
        return cleaned_data

    def _has_phone_field(self):
        """Avoid phone field errors."""
        return False

    def validate(self, data):
        """Ensure only super_admin, admin, or public registration is allowed."""
        user = self.context['request'].user
        # Allow public registration if user is not authenticated
        if user.is_authenticated and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can create users via this endpoint.")
        return data
