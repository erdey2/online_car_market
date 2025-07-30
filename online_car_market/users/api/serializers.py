from rest_framework import serializers
from ..models import User
from dj_rest_auth.registration.serializers import RegisterSerializer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'date_joined',
            'is_active', 'is_staff', 'role', 'description', 'permissions'
        ]
        read_only_fields = ['id', 'date_joined', 'is_active', 'is_staff']

    def validate_email(self, value):
        """Ensure email is unique (excluding the current instance)."""
        if self.instance is None and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_role(self, value):
        """Ensure role is one of the allowed choices."""
        valid_roles = [choice[0] for choice in User.role.field.choices]
        if value not in valid_roles:
            raise serializers.ValidationError(f"Invalid role. Must be one of: {valid_roles}")
        return value


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
