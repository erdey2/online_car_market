from rest_framework import serializers
from rolepermissions.roles import get_user_roles
from rolepermissions.checkers import has_role
from ..models import User
import re
from dj_rest_auth.registration.serializers import RegisterSerializer
import bleach

class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined', 'is_active', 'roles', 'is_staff', 'description', 'roles']
        read_only_fields = ['id', 'date_joined', 'is_active', 'is_staff']

    def get_roles(self, obj):
        """Return list of role names for the user."""
        return [role.__name__.lower() for role in get_user_roles(obj)]

    def validate_email(self, value):
        """Validate and sanitize email."""
        if not value:
            raise serializers.ValidationError("Email is required.")
        cleaned_email = bleach.clean(value.strip(), tags=[], strip=True)
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', cleaned_email):
            raise serializers.ValidationError("Invalid email format.")
        if User.objects.filter(email=cleaned_email).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("Email already exists.")
        return cleaned_email

    def validate_first_name(self, value):
        """Sanitize and validate first name."""
        if not value:
            raise serializers.ValidationError("First name is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("First name cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z\s-]+$', cleaned_value):
            raise serializers.ValidationError("First name can only contain letters, spaces, or hyphens.")
        return cleaned_value

    def validate_last_name(self, value):
        """Sanitize and validate last name."""
        if not value:
            raise serializers.ValidationError("Last name is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Last name cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z\s-]+$', cleaned_value):
            raise serializers.ValidationError("Last name can only contain letters, spaces, or hyphens.")
        return cleaned_value

    def validate_description(self, value):
        """Ensure description does not exceed 500 characters."""
        if value and len(value) > 500:
            raise serializers.ValidationError("Description cannot exceed 500 characters.")
        return value

    def validate(self, data):
        """Ensure only super_admin or admin can create/update users."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can create users.")
        if self.instance and self.instance != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError(
                "Only super admins, admins, or the user themselves can update this profile.")
        return data

class CustomRegisterSerializer(RegisterSerializer):
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    def get_cleaned_data(self):
        cleaned_data = super().get_cleaned_data()
        cleaned_data['first_name'] = self.validated_data.get('first_name', '')
        cleaned_data['last_name'] = self.validated_data.get('last_name', '')
        return cleaned_data

    def _has_phone_field(self):
        # Required to avoid AttributeError even if not using phone
        return False
