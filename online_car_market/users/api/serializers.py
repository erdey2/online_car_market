from rest_framework import serializers
from rolepermissions.roles import get_user_roles
from rolepermissions.checkers import has_role
from ..models import User
import re
from dj_rest_auth.registration.serializers import RegisterSerializer

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
        """Ensure email is unique and follows valid format."""
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', value):
            raise serializers.ValidationError("Invalid email format.")
        if self.instance is None and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_first_name(self, value):
        """Ensure first_name is valid."""
        if not value:
            raise serializers.ValidationError("First name is required.")
        if len(value) > 50:
            raise serializers.ValidationError("First name cannot exceed 50 characters.")
        if not re.match(r'^[a-zA-Z\s-]+$', value):
            raise serializers.ValidationError("First name can only contain letters, spaces, or hyphens.")
        return value

    def validate_last_name(self, value):
        """Ensure last_name is valid."""
        if not value:
            raise serializers.ValidationError("Last name is required.")
        if len(value) > 50:
            raise serializers.ValidationError("Last name cannot exceed 50 characters.")
        if not re.match(r'^[a-zA-Z\s-]+$', value):
            raise serializers.ValidationError("Last name can only contain letters, spaces, or hyphens.")
        return value

    def validate_description(self, value):
        """Ensure description does not exceed 500 characters."""
        if value and len(value) > 500:
            raise serializers.ValidationError("Description cannot exceed 500 characters.")
        return value

    def validate(self, data):
        """Ensure only super admins can modify is_staff or is_active."""
        if self.context['request'].user and not has_role(self.context['request'].user, 'super_admin'):
            if 'is_staff' in data or 'is_active' in data:
                raise serializers.ValidationError("Only super admins can modify is_staff or is_active.")
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
