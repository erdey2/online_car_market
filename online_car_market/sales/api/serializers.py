from rest_framework import serializers
from rolepermissions.checkers import has_role
from ..models import Sale, Lead, Car, User
from online_car_market.buyers.models import Buyer
from online_car_market.brokers.models import Broker
import re
import bleach

class SaleSerializer(serializers.ModelSerializer):
    buyer = serializers.PrimaryKeyRelatedField(queryset=Buyer.objects.all())
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())
    broker = serializers.PrimaryKeyRelatedField(queryset=Broker.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Sale
        fields = ['id', 'buyer', 'car', 'broker', 'price', 'date']
        read_only_fields = ['id', 'date']

    def validate_price(self, value):
        """Validate price."""
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        if value > 100000000:
            raise serializers.ValidationError("Price cannot exceed 100,000,000.")
        return value

    def validate_buyer(self, value):
        """Ensure buyer has buyer role."""
        if not has_role(value.user, 'buyer'):
            raise serializers.ValidationError("The assigned user must have the buyer role.")
        return value

    def validate_broker(self, value):
        """Ensure broker has broker role."""
        if value and not has_role(value.user, 'broker'):
            raise serializers.ValidationError("The assigned user must have the broker role.")
        return value

    def validate_car(self, value):
        """Ensure car is available or reserved."""
        if value.status not in ['available', 'reserved']:
            raise serializers.ValidationError("The car must be available or reserved for sale.")
        return value

    def validate(self, data):
        """Ensure only sales, admins, or super admins can create/update sales."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'sales']):
            raise serializers.ValidationError("Only sales, admins, or super admins can create sales.")
        if self.instance and not has_role(user, ['super_admin', 'admin', 'sales']):
            raise serializers.ValidationError("Only sales, admins, or super admins can update sales.")
        if data.get('price') and data.get('car') and data['price'] < data['car'].price * 0.9:
            raise serializers.ValidationError("Sale price cannot be less than 90% of the car's listed price.")
        return data

class LeadSerializer(serializers.ModelSerializer):
    assigned_sales = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Lead
        fields = ['id', 'name', 'contact', 'status', 'assigned_sales', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        """Sanitize and validate name."""
        if not value:
            raise serializers.ValidationError("Name is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Name cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z\s-]+$', cleaned_value):
            raise serializers.ValidationError("Name can only contain letters, spaces, or hyphens.")
        return cleaned_value

    def validate_contact(self, value):
        """Sanitize and validate email or Ethiopian phone number."""
        if not value:
            raise serializers.ValidationError("Contact is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        phone_regex = r'^\+251[79]\d{8}$'
        if not (re.match(email_regex, cleaned_value) or re.match(phone_regex, cleaned_value)):
            raise serializers.ValidationError("Contact must be a valid email or Ethiopian phone number (e.g., +251912345678).")
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Contact cannot exceed 100 characters.")
        return cleaned_value

    def validate_status(self, value):
        """Sanitize and validate status."""
        valid_statuses = ['inquiry', 'negotiation', 'closed']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(valid_statuses)}.")
        return cleaned_value

    def validate_assigned_sales(self, value):
        """Ensure assigned_sales has sales role."""
        if value and not has_role(value, 'sales'):
            raise serializers.ValidationError("The assigned user must have the sales role.")
        return value

    def validate(self, data):
        """Ensure only sales, admins, or super admins can create/update leads."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'sales']):
            raise serializers.ValidationError("Only sales, admins, or super admins can create leads.")
        if self.instance and not has_role(user, ['super_admin', 'admin', 'sales']):
            raise serializers.ValidationError("Only sales, admins, or super admins can update leads.")
        return data
