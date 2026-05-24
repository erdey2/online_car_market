from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from rolepermissions.checkers import has_role
from online_car_market.sales.models import Sale, Lead
from online_car_market.inventory.models import Car
from online_car_market.brokers.models import BrokerProfile
from online_car_market.dealers.models import DealerProfile, DealerStaff
from online_car_market.sales.service.lead_service import LeadService
from django.contrib.auth import get_user_model
from online_car_market.dealers.models import DealerStaff

User = get_user_model()

class SaleSerializer(serializers.ModelSerializer):
    buyer = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())
    broker = serializers.PrimaryKeyRelatedField(queryset=BrokerProfile.objects.all(), required=False, allow_null=True)
    dealer = serializers.PrimaryKeyRelatedField(queryset=DealerProfile.objects.all(), required=False, allow_null=True)
    buyer_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'buyer', 'buyer_info', 'car', 'broker', 'dealer', 'price', 'date']
        read_only_fields = ['id', 'date', 'buyer_info']

    @extend_schema_field({
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "email": {"type": "string"},
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
            "contact": {"type": "string"},
            "loyalty_points": {"type": "integer"},
        }
    })
    def get_buyer_info(self, obj):
        """Return detailed buyer info including BuyerProfile."""
        try:
            profile = obj.buyer.profile
            buyer_profile = getattr(profile, 'buyer_profile', None)
            return {
                "id": obj.buyer.id,
                "email": obj.buyer.email,
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "contact": profile.contact,
                "loyalty_points": getattr(buyer_profile, "loyalty_points", 0)
            }
        except AttributeError:
            return None

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        if value > 100_000_000:
            raise serializers.ValidationError("Price cannot exceed 100,000,000.")
        return value

    def validate_buyer(self, value):
        """Ensure buyer has the 'buyer' role."""
        if not has_role(value, 'buyer'):
            raise serializers.ValidationError("The assigned user must have the buyer role.")
        return value

    def validate_car(self, value):
        """Ensure the car is available or reserved."""
        if value.status not in ['available', 'reserved']:
            raise serializers.ValidationError("The car must be available or reserved for sale.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        car = data.get('car')

        # Role-based access
        if has_role(user, 'broker'):
            try:
                broker_profile = BrokerProfile.objects.get(profile__user=user)
                if car.broker != broker_profile:
                    raise serializers.ValidationError("You can only create sales for your own cars.")
                data['broker'] = broker_profile
            except BrokerProfile.DoesNotExist:
                raise serializers.ValidationError("Broker profile not found.")

        elif has_role(user, 'dealer'):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
                if car.dealer != dealer_profile:
                    raise serializers.ValidationError("You can only create sales for your own cars.")
                data['dealer'] = dealer_profile
            except DealerProfile.DoesNotExist:
                raise serializers.ValidationError("Dealer profile not found.")

        elif has_role(user, 'seller'):
            try:
                staff = DealerStaff.objects.get(user=user, role='seller')
                if car.dealer != staff.dealer:
                    raise serializers.ValidationError("You can only sell cars belonging to your dealer.")
                data['dealer'] = staff.dealer
            except DealerStaff.DoesNotExist:
                raise serializers.ValidationError("You are not assigned to any dealer as a seller.")

        elif has_role(user, ['super_admin', 'admin']):
            # Admins can assign broker or dealer freely
            pass
        else:
            raise serializers.ValidationError("You don't have permission to create a sale.")

        # Validate car ownership consistency
        broker = data.get('broker')
        dealer = data.get('dealer')
        if broker and dealer:
            raise serializers.ValidationError("Car cannot belong to both broker and dealer.")
        if not broker and not dealer:
            raise serializers.ValidationError("Car must belong to a broker or a dealer.")

        return data

    def create(self, validated_data):
        """Create sale and mark car as sold."""
        car = validated_data['car']
        sale = super().create(validated_data)
        car.status = 'sold'
        car.save()
        return sale

    def update(self, instance, validated_data):
        """Update sale and mark car as sold."""
        car = validated_data.get('car', instance.car)
        sale = super().update(instance, validated_data)
        car.status = 'sold'
        car.save()
        return sale

class LeadSerializer(serializers.ModelSerializer):
    buyer_name = serializers.SerializerMethodField()
    car_info = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = "__all__"
        read_only_fields = [
            "status",
            "assigned_sales",
            "closed_at",
            "closed_by",
        ]

    def get_buyer_name(self, obj):
        if not obj.buyer:
            return obj.name

        profile = getattr(obj.buyer, "profile", None)

        if profile:
            first_name = getattr(profile, "first_name", "")
            last_name = getattr(profile, "last_name", "")
            full_name = f"{first_name} {last_name}".strip()

            if full_name:
                return full_name

        return obj.buyer.email

    def get_car_info(self, obj):
        if obj.car:
            return {
                "id": obj.car.id,
                "make": obj.car.make,
                "model": obj.car.model,
            }
        return None

class LeadCreateSerializer(serializers.ModelSerializer):
    car_id = serializers.PrimaryKeyRelatedField(
        queryset=Car.objects.all(),
        source="car",
    )

    class Meta:
        model = Lead
        fields = ["car_id", "name", "contact"]

    def validate_contact(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                "Contact cannot be empty."
            )
        return value

    def validate(self, attrs):
        car = attrs.get("car")
        contact = attrs["contact"]

        if Lead.objects.filter(
            contact__iexact=contact,
            car=car
        ).exists():
            raise serializers.ValidationError(
                "A lead with this contact already exists for this car."
            )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        buyer = (
            request.user
            if request and request.user.is_authenticated
            else None
        )

        car = validated_data.pop("car")

        return LeadService.create_lead(
            car=car,
            name=validated_data["name"],
            contact=validated_data["contact"],
            buyer=buyer
        )

class LeadStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=Lead.LeadStatus.choices,
        help_text="Allowed values: inquiry, contacted, negotiation, closed, lost, cancelled"
    )

    def validate_status(self, value):
        request = self.context.get("request")
        user = request.user if request else None

        dealer_profile = getattr(
            getattr(user, "profile", None),
            "dealer_profile",
            None
        )

        broker_profile = getattr(
            getattr(user, "profile", None),
            "broker_profile",
            None
        )

        seller_assignment = DealerStaff.objects.filter(
            user=user,
            role="seller"
        ).exists()

        if value == Lead.LeadStatus.CLOSED:
            can_close = (
                user
                and (
                    user.is_superuser
                    or dealer_profile
                    or broker_profile
                    or seller_assignment
                )
            )

            if not can_close:
                raise serializers.ValidationError(
                    "Only sellers, dealers, brokers, or admins can close a lead."
                )

        return value

    def update(self, instance, validated_data):
        request = self.context.get("request")
        return LeadService.update_status(
            lead=instance,
            new_status=validated_data["status"],
            user=request.user
        )

class LeadAnalyticsSerializer(serializers.Serializer):
    total_leads = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    leads_by_status = serializers.ListField()
    avg_time_to_close = serializers.DurationField(allow_null=True)




