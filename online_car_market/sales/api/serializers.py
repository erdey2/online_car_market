from rest_framework import serializers
from rolepermissions.checkers import has_role
from online_car_market.sales.models import Sale, Lead
from online_car_market.inventory.models import Car
from online_car_market.buyers.models import BuyerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.dealers.models import DealerProfile
from django.contrib.auth import get_user_model
import re
import bleach

User = get_user_model()

class SaleSerializer(serializers.ModelSerializer):
    buyer = serializers.PrimaryKeyRelatedField(queryset=BuyerProfile.objects.all())
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())
    broker = serializers.PrimaryKeyRelatedField(queryset=BrokerProfile.objects.all(), required=False, allow_null=True)

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
        if not has_role(value.profile.user, 'buyer'):
            raise serializers.ValidationError("The assigned user must have the buyer role.")
        return value

    def validate_broker(self, value):
        """Ensure broker has broker role and can post cars."""
        if value:
            if not has_role(value.profile.user, 'broker'):
                raise serializers.ValidationError("The assigned user must have the broker role.")
            if not value.can_post:
                raise serializers.ValidationError("Broker must have paid to post cars.")
        return value

    def validate_car(self, value):
        """Ensure car is available or reserved and belongs to broker or dealer."""
        if value.status not in ['available', 'reserved']:
            raise serializers.ValidationError("The car must be available or reserved for sale.")
        return value

    def validate(self, data):
        """Ensure user has permission and car ownership is valid."""
        user = self.context['request'].user
        car = data.get('car')
        broker = data.get('broker')

        # Permission check
        allowed_roles = ['super_admin', 'admin']
        if has_role(user, 'broker'):
            try:
                broker_profile = BrokerProfile.objects.get(profile__user=user)
                if car.broker != broker_profile:
                    raise serializers.ValidationError("Brokers can only create sales for their own cars.")
                allowed_roles.append('broker')
            except BrokerProfile.DoesNotExist:
                raise serializers.ValidationError("Broker profile not found.")
        elif has_role(user, 'dealer'):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
                if car.dealer != dealer_profile:
                    raise serializers.ValidationError("Dealers can only create sales for their own cars.")
                allowed_roles.append('dealer')
            except DealerProfile.DoesNotExist:
                raise serializers.ValidationError("Dealer profile not found.")

        if not has_role(user, allowed_roles):
            raise serializers.ValidationError(
                "Only brokers (for their cars), dealers (for their cars), admins, or super admins can create/update sales."
            )

        # Validate car ownership
        if broker and car.broker != broker:
            raise serializers.ValidationError("The car must belong to the specified broker.")
        if not broker and not car.dealer:
            raise serializers.ValidationError("The car must belong to a broker or dealer.")
        if broker and car.dealer:
            raise serializers.ValidationError("The car cannot belong to both a broker and a dealer.")

        # Price validation (allow admins to override)
        if (data.get('price') and data.get('car') and
                data['price'] < data['car'].price * 0.9 and
                not has_role(user, ['super_admin', 'admin'])):
            raise serializers.ValidationError("Sale price cannot be less than 90% of the car's listed price.")

        return data

    def create(self, validated_data):
        """Set car status to sold upon sale creation."""
        car = validated_data['car']
        sale = super().create(validated_data)
        car.status = 'sold'
        car.save()
        return sale

    def update(self, instance, validated_data):
        """Set car status to sold upon sale update."""
        car = validated_data.get('car', instance.car)
        sale = super().update(instance, validated_data)
        car.status = 'sold'
        car.save()
        return sale

class LeadSerializer(serializers.ModelSerializer):
    assigned_sales = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Lead
        fields = ['id', 'name', 'contact', 'status', 'assigned_sales', 'car', 'created_at']
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
        # Check for duplicate contacts
        if Lead.objects.filter(contact=cleaned_value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("A lead with this contact already exists.")
        return cleaned_value

    def validate_status(self, value):
        """Sanitize and validate status."""
        valid_statuses = ['inquiry', 'negotiation', 'closed']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(valid_statuses)}.")
        # Prevent invalid status transitions
        if self.instance and self.instance.status == 'closed' and cleaned_value != 'closed':
            raise serializers.ValidationError("Cannot change status from 'closed' to another status.")
        return cleaned_value

    def validate_assigned_sales(self, value):
        """Ensure assigned_sales has broker, dealer, or sales role."""
        if value and not has_role(value, ['broker', 'dealer', 'sales']):
            raise serializers.ValidationError("The assigned user must have the broker, dealer, or sales role.")
        return value

    def validate_car(self, value):
        """Ensure car is valid and belongs to broker or dealer."""
        if value:
            if value.status not in ['available', 'reserved']:
                raise serializers.ValidationError("The car must be available or reserved.")
            if not (value.broker or value.dealer):
                raise serializers.ValidationError("The car must belong to a broker or dealer.")
        return value

    def validate(self, data):
        """Ensure user has permission and car ownership is valid."""
        user = self.context['request'].user
        car = data.get('car')
        assigned_sales = data.get('assigned_sales')

        # Permission check
        allowed_roles = ['super_admin', 'admin']
        if has_role(user, 'broker'):
            try:
                broker_profile = BrokerProfile.objects.get(profile__user=user)
                if car and car.broker != broker_profile:
                    raise serializers.ValidationError("Brokers can only create leads for their own cars.")
                if assigned_sales and not has_role(assigned_sales, ['broker', 'sales']):
                    raise serializers.ValidationError("Assigned user must be a broker or sales for broker leads.")
                allowed_roles.append('broker')
            except BrokerProfile.DoesNotExist:
                raise serializers.ValidationError("Broker profile not found.")
        elif has_role(user, 'dealer'):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
                if car and car.dealer != dealer_profile:
                    raise serializers.ValidationError("Dealers can only create leads for their own cars.")
                if assigned_sales and not has_role(assigned_sales, ['dealer', 'sales']):
                    raise serializers.ValidationError("Assigned user must be a dealer or sales for dealer leads.")
                allowed_roles.append('dealer')
            except DealerProfile.DoesNotExist:
                raise serializers.ValidationError("Dealer profile not found.")

        if not has_role(user, allowed_roles):
            raise serializers.ValidationError(
                "Only brokers (for their cars), dealers (for their cars), admins, or super admins can create/update leads."
            )

        return data
