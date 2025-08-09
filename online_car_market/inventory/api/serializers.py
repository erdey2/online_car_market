from rest_framework import serializers
from rolepermissions.checkers import has_role, has_permission
from ..models import Car, CarImage
from online_car_market.dealers.models import Dealer
from django.contrib.auth import get_user_model
import re
import bleach
from datetime import datetime

User = get_user_model()

class CarImageSerializer(serializers.ModelSerializer):
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())
    # Accept file uploads; use_url=True makes the field representation return a URL
    image = serializers.ImageField(required=False, allow_null=True, use_url=True)
    # Optionally accept existing Cloudinary public_id or full URL
    image_public_id = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = CarImage
        fields = ["id", "car", "image", "image_public_id", "is_featured", "caption", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]

    def validate_image_public_id(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        # allow typical cloudinary public-id style (letters/numbers/_- and slashes) or a full http(s) url
        if not re.match(r'^[A-Za-z0-9_-]+(\/[A-Za-z0-9_-]+)*$', cleaned) and not cleaned.startswith(("http://", "https://")):
            raise serializers.ValidationError("Invalid Cloudinary public ID or URL.")
        return cleaned

    def validate_caption(self, value):
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 255:
                raise serializers.ValidationError("Caption cannot exceed 255 characters.")
            return cleaned_value
        return value

    def validate_is_featured(self, value):
        # If setting featured=true, ensure no other featured image exists for this car (except self on update)
        if not value:
            return value

        # Determine car id
        car_obj = None
        if self.instance:
            car_obj = self.instance.car
        else:
            # incoming car is a PK from validated_data (PrimaryKeyRelatedField)
            car_pk = self.initial_data.get("car")
            try:
                car_obj = Car.objects.get(pk=car_pk) if car_pk else None
            except Car.DoesNotExist:
                car_obj = None

        if car_obj:
            qs = CarImage.objects.filter(car=car_obj, is_featured=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Another image is already featured for this car.")
        return value

    def validate(self, data):
        user = self.context["request"].user
        # create: instance is None
        if self.instance is None:
            if not has_role(user, ["super_admin", "admin", "dealer"]):
                raise serializers.ValidationError("Only dealers, admins, or super admins can create car images.")
            car = data.get("car")
            if car and not has_role(user, ["super_admin", "admin"]):
                # non-admin/ non-super must be owner of the car (posted_by)
                if not hasattr(car, "posted_by") or car.posted_by != user:
                    raise serializers.ValidationError("Only the car owner or admins can add images.")
        else:
            # update: allow only owner or admin/super_admin
            car = data.get("car", self.instance.car)
            if not has_role(user, ["super_admin", "admin"]):
                if not hasattr(car, "posted_by") or car.posted_by != user:
                    raise serializers.ValidationError("Only the car owner or admins can update this car image.")
        return data

    def create(self, validated_data):
        public_id = validated_data.pop("image_public_id", None)
        image_file = validated_data.pop("image", None)
        car = validated_data.get("car")

        instance = CarImage.objects.create(car=car, **{k: v for k, v in validated_data.items() if k not in ("image",)})
        # assign image source: prefer public_id if provided, else uploaded file
        if public_id:
            # assign string public id or URL directly to CloudinaryField
            instance.image = public_id
        elif image_file:
            instance.image = image_file
        instance.save()
        return instance

    def update(self, instance, validated_data):
        public_id = validated_data.pop("image_public_id", None)
        image_file = validated_data.pop("image", None)

        # update regular fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if public_id:
            instance.image = public_id
        elif image_file:
            instance.image = image_file

        instance.save()
        return instance

class CarSerializer(serializers.ModelSerializer):
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all())
    posted_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault())
    images = CarImageSerializer(many=True, read_only=True)
    verification_status = serializers.ChoiceField(choices=Car.VERIFICATION_STATUSES, read_only=True)

    class Meta:
        model = Car
        fields = ['id', 'make', 'model', 'year', 'price', 'mileage', 'fuel_type', 'status', 'dealer', 'posted_by', 'verification_status', 'created_at', 'updated_at', 'images']
        read_only_fields = ['id', 'created_at', 'updated_at', 'verification_status']

    def validate_make(self, value):
        """Sanitize and validate make."""
        if not value:
            raise serializers.ValidationError("Make is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Make cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', cleaned_value):
            raise serializers.ValidationError("Make can only contain letters, numbers, spaces, or hyphens.")
        return cleaned_value

    def validate_model(self, value):
        """Sanitize and validate model."""
        if not value:
            raise serializers.ValidationError("Model is required.")
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Model cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', cleaned_value):
            raise serializers.ValidationError("Model can only contain letters, numbers, spaces, or hyphens.")
        return cleaned_value

    def validate_year(self, value):
        """Validate year."""
        current_year = datetime.now().year
        if not 1900 <= value <= current_year + 1:
            raise serializers.ValidationError(f"Year must be between 1900 and {current_year + 1}.")
        return value

    def validate_price(self, value):
        """Validate price."""
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        if value > 100000000:
            raise serializers.ValidationError("Price cannot exceed 100,000,000.")
        return value

    def validate_mileage(self, value):
        """Validate mileage."""
        if value < 0:
            raise serializers.ValidationError("Mileage cannot be negative.")
        if value > 1000000:
            raise serializers.ValidationError("Mileage cannot exceed 1,000,000 km.")
        return value

    def validate_fuel_type(self, value):
        """Sanitize and validate fuel type."""
        valid_types = ['electric', 'hybrid', 'petrol', 'diesel']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_types:
            raise serializers.ValidationError(f"Fuel type must be one of: {', '.join(valid_types)}.")
        return cleaned_value

    def validate_status(self, value):
        """Sanitize and validate status."""
        valid_statuses = ['available', 'reserved', 'sold', 'pending_inspection', 'under_maintenance', 'delivered', 'archived']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(valid_statuses)}.")
        return cleaned_value

    def validate_dealer(self, value):
        """Ensure dealer has dealer role and matches user."""
        if not has_role(value.user, 'dealer'):
            raise serializers.ValidationError("The assigned user must have the dealer role.")
        user = self.context['request'].user
        if value.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the dealer owner or admins can assign this dealer.")
        return value

    def validate(self, data):
        """Ensure only authorized users can create/update cars."""
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'dealer']):
            raise serializers.ValidationError("Only dealers, admins, or super admins can create cars.")
        if self.instance and data.get('posted_by') and data['posted_by'] != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the car owner or admins can update this car.")
        return data

class VerifyCarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['verification_status']
        read_only_fields = []

    def validate_verification_status(self, value):
        """Ensure valid verification status."""
        valid_statuses = ['pending', 'verified', 'rejected']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Verification status must be one of: {', '.join(valid_statuses)}.")
        return cleaned_value

    def validate(self, data):
        """Ensure only admins or super admins can verify cars."""
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify cars.")
        return data
