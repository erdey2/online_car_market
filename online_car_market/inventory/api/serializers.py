from rest_framework import serializers
from rolepermissions.checkers import has_role
from ..models import Car, CarImage
from online_car_market.dealers.models import Dealer
from django.contrib.auth import get_user_model
import re
import bleach
from datetime import datetime

User = get_user_model()


# ---------------- CarImage Serializer ----------------
class CarImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)  # Always return full URL
    image_file = serializers.ImageField(write_only=True, required=False)  # For file uploads
    image_public_id = serializers.CharField(write_only=True, required=False, allow_blank=True)  # For public_id uploads

    class Meta:
        model = CarImage
        fields = ["id", "car", "image_url", "image_file", "image_public_id", "is_featured", "caption", "uploaded_at",]
        read_only_fields = ["id", "uploaded_at"]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url  # CloudinaryField returns full URL
        return None

    def validate_image_public_id(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if not re.match(r'^[A-Za-z0-9_-]+(\/[A-Za-z0-9_-]+)*$', cleaned) \
               and not cleaned.startswith(("http://", "https://")):
                raise serializers.ValidationError("Invalid Cloudinary public ID or URL.")
            return cleaned
        return value

    def validate_caption(self, value):
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 255:
                raise serializers.ValidationError("Caption cannot exceed 255 characters.")
            return cleaned_value
        return value

    def validate(self, data):
        user = self.context["request"].user
        car = data.get("car") or getattr(self.instance, "car", None)

        if not car:
            return data

        if self.instance is None:  # Creating
            if not has_role(user, ["super_admin", "admin", "dealer"]):
                raise serializers.ValidationError("Only dealers, admins, or super admins can create car images.")
            if not has_role(user, ["super_admin", "admin"]) and getattr(car, "posted_by", None) != user:
                raise serializers.ValidationError("Only the car owner or admins can add images.")
        else:  # Updating
            if not has_role(user, ["super_admin", "admin"]) and getattr(car, "posted_by", None) != user:
                raise serializers.ValidationError("Only the car owner or admins can update this image.")

        return data

    def create(self, validated_data):
        image_file = validated_data.pop("image_file", None)
        image_public_id = validated_data.pop("image_public_id", None)
        instance = CarImage(**validated_data)

        if image_file:
            instance.image = image_file
        elif image_public_id:
            instance.image = image_public_id  # Cloudinary will resolve public_id

        instance.save()
        return instance


# ---------------- Car Serializer ----------------
class CarSerializer(serializers.ModelSerializer):
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all())
    posted_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault())
    images = CarImageSerializer(many=True, read_only=True)
    uploaded_images = CarImageSerializer(many=True, write_only=True, required=False)

    verification_status = serializers.ChoiceField(choices=Car.VERIFICATION_STATUSES, read_only=True)

    class Meta:
        model = Car
        fields = [
            'id', 'make', 'model', 'year', 'price', 'mileage', 'fuel_type', 'status',
            'dealer', 'posted_by', 'verification_status', 'created_at', 'updated_at',
            'images', 'uploaded_images'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'verification_status']

    def validate_make(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if not cleaned:
            raise serializers.ValidationError("Make is required.")
        if len(cleaned) > 100:
            raise serializers.ValidationError("Make cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', cleaned):
            raise serializers.ValidationError("Make can only contain letters, numbers, spaces, or hyphens.")
        return cleaned

    def validate_model(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if not cleaned:
            raise serializers.ValidationError("Model is required.")
        if len(cleaned) > 100:
            raise serializers.ValidationError("Model cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', cleaned):
            raise serializers.ValidationError("Model can only contain letters, numbers, spaces, or hyphens.")
        return cleaned

    def validate_year(self, value):
        current_year = datetime.now().year
        if not 1900 <= value <= current_year + 1:
            raise serializers.ValidationError(f"Year must be between 1900 and {current_year + 1}.")
        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        if value > 100000000:
            raise serializers.ValidationError("Price cannot exceed 100,000,000.")
        return value

    def validate_mileage(self, value):
        if value < 0:
            raise serializers.ValidationError("Mileage cannot be negative.")
        if value > 1000000:
            raise serializers.ValidationError("Mileage cannot exceed 1,000,000 km.")
        return value

    def validate_fuel_type(self, value):
        valid_types = ['electric', 'hybrid', 'petrol', 'diesel']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_types:
            raise serializers.ValidationError(f"Fuel type must be one of: {', '.join(valid_types)}.")
        return cleaned_value

    def validate_status(self, value):
        valid_statuses = [c[0] for c in Car.STATUS_CHOICES]
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(valid_statuses)}.")
        return cleaned_value

    def validate_dealer(self, value):
        if not has_role(value.user, 'dealer'):
            raise serializers.ValidationError("The assigned user must have the dealer role.")
        user = self.context['request'].user
        if value.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the dealer owner or admins can assign this dealer.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'dealer']):
            raise serializers.ValidationError("Only dealers, admins, or super admins can create cars.")
        if self.instance and data.get('posted_by') and data['posted_by'] != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the car owner or admins can update this car.")
        return data

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        car = Car.objects.create(**validated_data)

        for img_data in uploaded_images:
            img_data['car'] = car
            CarImageSerializer(context=self.context).create(img_data)

        return car

# ---------------- Verify Car Serializer ----------------
class VerifyCarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['verification_status']

    def validate_verification_status(self, value):
        valid_statuses = ['pending', 'verified', 'rejected']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Verification status must be one of: {', '.join(valid_statuses)}.")
        return cleaned_value

    def validate(self, data):
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify cars.")
        return data
