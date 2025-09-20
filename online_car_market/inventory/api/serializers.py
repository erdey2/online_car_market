from django.utils import timezone
from django.db.models import Avg
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from rolepermissions.checkers import has_role
from ..models import Car, CarImage, CarMake, CarModel, FavoriteCar, CarView
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.bids.api.serializers import BidSerializer
from online_car_market.payment.models import Payment
from django.contrib.auth import get_user_model
import re
import bleach
from datetime import datetime

User = get_user_model()

class CarMakeSerializer(serializers.ModelSerializer):
    """
    Serializer for CarMake model.
    Provides read-only access to id, name, and slug.
    Validates unique make names and sanitizes input for create/update.
    """
    class Meta:
        model = CarMake
        fields = ['id', 'name']
        read_only_fields = ['id']

    def validate_name(self, value):
        """
        Validate make name: non-empty, max 100 chars, unique, sanitized.
        """
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if not cleaned:
            raise serializers.ValidationError("Make name cannot be empty.")
        if len(cleaned) > 100:
            raise serializers.ValidationError("Make name cannot exceed 100 characters.")
        if CarMake.objects.filter(name=cleaned).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This make name already exists.")
        return cleaned

    def validate(self, data):
        """
        Restrict create/update to admin or superadmin users.
        """
        if self.context['request'].method in ['POST', 'PUT', 'PATCH']:
            user = self.context['request'].user
            if not has_role(user, ['admin', 'super_admin']) and not user.is_superuser:
                raise serializers.ValidationError("Only admins or super admins can create or update makes.")
        return data

class CarModelSerializer(serializers.ModelSerializer):
    """
    Serializer for CarModel model.
    Provides read-only access to id, name, slug, and nested make details.
    Validates unique model names per make and sanitizes input for create/update.
    """
    make = CarMakeSerializer(read_only=True)
    make_id = serializers.PrimaryKeyRelatedField(
        queryset=CarMake.objects.all(),
        source='make',
        write_only=True,
        required=True
    )

    class Meta:
        model = CarModel
        fields = ['id', 'name', 'make', 'make_id']
        read_only_fields = ['id', 'make']

    def validate_name(self, value):
        """
        Validate model name: non-empty, max 100 chars, unique per make, sanitized.
        """
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if not cleaned:
            raise serializers.ValidationError("Model name cannot be empty.")
        if len(cleaned) > 100:
            raise serializers.ValidationError("Model name cannot exceed 100 characters.")
        make = self.initial_data.get('make_id') or (self.instance.make.id if self.instance else None)
        if make and CarModel.objects.filter(make_id=make, name=cleaned).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("This model name already exists for the selected make.")
        return cleaned

    def validate(self, data):
        """
        Restrict create/update to admin or superadmin users.
        """
        if self.context['request'].method in ['POST', 'PUT', 'PATCH']:
            user = self.context['request'].user
            if not has_role(user, ['admin', 'super_admin']) and not user.is_superuser:
                raise serializers.ValidationError("Only admins or super admins can create or update models.")
        return data

class CarImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)
    image_file = serializers.ImageField(write_only=True, required=False)  # for uploads
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all(), required=False)

    class Meta:
        model = CarImage
        fields = ["id", "car", "image_file", "image_url", "is_featured", "caption", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at", "image_url"]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image_url(self, obj):
        return obj.image.url if obj.image else None

    def validate_caption(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 255:
                raise serializers.ValidationError("Caption cannot exceed 255 characters.")
            return cleaned
        return value

    def validate_image_file(self, value):
        if value:
            max_size = 5 * 1024 * 1024  # 5MB
            if value.size > max_size:
                raise serializers.ValidationError("Image file size cannot exceed 5MB.")
            return value
        return value

    def validate(self, data):
        car = data.get("car") or getattr(self.instance, "car", None)
        user = self.context["request"].user
        if self.instance is None:
            if not has_role(user, ["super_admin", "admin", "dealer", "broker"]):
                raise serializers.ValidationError("Only brokers, dealers, admins, or super admins can create car images.")
            if car and not has_role(user, ["super_admin", "admin"]) and getattr(car, "posted_by", None) != user:
                raise serializers.ValidationError("Only the car owner or admins can add images.")
        return data

    def create(self, validated_data):
        car = validated_data.pop("car", None)
        image_file = validated_data.pop("image_file")
        instance = CarImage(**validated_data)
        if car:
            instance.car = car
        instance.image = image_file  # CloudinaryField handles the upload automatically
        instance.save()
        return instance

class CarSerializer(serializers.ModelSerializer):
    dealer = serializers.PrimaryKeyRelatedField(
        queryset=DealerProfile.objects.all(), required=False, allow_null=True
    )
    broker = serializers.PrimaryKeyRelatedField(
        queryset=BrokerProfile.objects.all(), required=False, allow_null=True
    )
    posted_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), default=serializers.CurrentUserDefault()
    )
    images = CarImageSerializer(many=True, read_only=True)
    uploaded_images = CarImageSerializer(many=True, write_only=True, required=False)
    bids = BidSerializer(many=True, read_only=True)
    verification_status = serializers.ChoiceField(
        choices=Car.VERIFICATION_STATUSES, read_only=True
    )
    make_ref = serializers.PrimaryKeyRelatedField(
        queryset=CarMake.objects.all(), required=False, allow_null=True
    )
    model_ref = serializers.PrimaryKeyRelatedField(
        queryset=CarModel.objects.all(), required=False, allow_null=True
    )
    dealer_average_rating = serializers.SerializerMethodField(read_only=True)
    broker_average_rating = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Car
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "verification_status",
            "priority",
            "dealer_average_rating",
            "broker_average_rating",
        ]

    # ---------------- Average Rating ----------------
    def get_dealer_average_rating(self, obj) -> float | None:
        if obj.dealer:
            avg_rating = obj.dealer.ratings.aggregate(Avg("rating"))["rating__avg"]
            return round(avg_rating, 1) if avg_rating else None
        return None

    def get_broker_average_rating(self, obj) -> float | None:
        if obj.broker:
            avg_rating = obj.broker.ratings.aggregate(Avg("rating"))["rating__avg"]
            return round(avg_rating, 1) if avg_rating else None
        return None

    # ---------------- Field Validations (same as yours) ----------------
    def validate_make(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned) > 100:
            raise serializers.ValidationError("Make cannot exceed 100 characters.")
        if not re.match(r"^[a-zA-Z0-9\s-]+$", cleaned):
            raise serializers.ValidationError("Invalid characters.")
        return cleaned

    def validate_model(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned) > 100:
            raise serializers.ValidationError("Model cannot exceed 100 characters.")
        if not re.match(r"^[a-zA-Z0-9\s-]+$", cleaned):
            raise serializers.ValidationError("Invalid characters.")
        return cleaned

    def validate_year(self, value):
        current_year = datetime.now().year
        if not 1900 <= value <= current_year + 1:
            raise serializers.ValidationError(f"Year must be 1900-{current_year+1}.")
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

    def validate_body_type(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            valid_types = [choice[0] for choice in Car.BODY_TYPES]
            if cleaned not in valid_types:
                raise serializers.ValidationError(
                    f"Body type must be one of: {', '.join(valid_types)}."
                )
            return cleaned
        return value

    def validate_fuel_type(self, value):
        valid_types = ["electric", "hybrid", "petrol", "diesel"]
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned not in valid_types:
            raise serializers.ValidationError(
                f"Fuel type must be one of: {', '.join(valid_types)}."
            )
        return cleaned

    def validate_exterior_color(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 20:
                raise serializers.ValidationError(
                    "Exterior color cannot exceed 20 characters."
                )
            if not re.match(r"^[a-zA-Z\s-]+$", cleaned):
                raise serializers.ValidationError(
                    "Invalid characters in exterior color."
                )
            return cleaned
        return value

    def validate_interior_color(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 20:
                raise serializers.ValidationError(
                    "Interior color cannot exceed 20 characters."
                )
            if not re.match(r"^[a-zA-Z\s-]+$", cleaned):
                raise serializers.ValidationError(
                    "Invalid characters in interior color."
                )
            return cleaned
        return value

    def validate_engine(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 100:
                raise serializers.ValidationError(
                    "Engine specification cannot exceed 100 characters."
                )
            if not re.match(r"^[a-zA-Z0-9\s\.\-L]+$", cleaned):
                raise serializers.ValidationError(
                    "Invalid characters in engine specification."
                )
            return cleaned
        return value

    def validate_drivetrain(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            valid_types = [choice[0] for choice in Car.DRIVETRAIN_TYPES]
            if cleaned not in valid_types:
                raise serializers.ValidationError(
                    f"Drivetrain type must be one of: {', '.join(valid_types)}."
                )
            return cleaned
        return value

    def validate_condition(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            valid_types = [choice[0] for choice in Car.CONDITIONS]
            if cleaned not in valid_types:
                raise serializers.ValidationError(
                    f"Condition must be one of: {', '.join(valid_types)}."
                )
            return cleaned
        return value

    def validate_trim(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 50:
                raise serializers.ValidationError("Trim cannot exceed 50 characters.")
            if not re.match(r"^[a-zA-Z0-9\s-]+$", cleaned):
                raise serializers.ValidationError("Invalid characters in trim.")
            return cleaned
        return value

    def validate_description(self, value):
        if value:
            return bleach.clean(value.strip(), tags=[], strip=True)
        return value

    def validate_status(self, value):
        valid_statuses = [c[0] for c in Car.STATUS_CHOICES]
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned not in valid_statuses:
            raise serializers.ValidationError(
                f"Status must be one of: {', '.join(valid_statuses)}."
            )
        return cleaned

    def validate_sale_type(self, value):
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        valid_types = [choice[0] for choice in Car.SALE_TYPES]
        if cleaned_value not in valid_types:
            raise serializers.ValidationError(
                f"Sale type must be one of: {', '.join(valid_types)}."
            )
        return cleaned_value

    def validate_auction_end(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Auction end time must be in the future.")
        return value

    def validate_dealer(self, value):
        if value and not has_role(value.profile.user, "dealer"):
            raise serializers.ValidationError("Dealer user must have dealer role.")
        user = self.context["request"].user
        if value and value.user != user and not has_role(user, ["super_admin", "admin"]):
            raise serializers.ValidationError(
                "Only dealer owner or admins can assign this dealer."
            )
        return value

    def validate_broker(self, value):
        if value and not has_role(value.profile.user, "broker"):
            raise serializers.ValidationError("Broker user must have broker role.")
        user = self.context["request"].user
        if value and value.profile.user != user and not has_role(
            user, ["super_admin", "admin"]
        ):
            raise serializers.ValidationError(
                "Only broker owner or admins can assign this broker."
            )
        return value

    def validate_model_ref(self, value):
        make_ref_id = self.initial_data.get("make_ref")
        if value and make_ref_id and value.make.id != int(make_ref_id):
            raise serializers.ValidationError(
                "Selected model must belong to the selected make."
            )
        return value

    # ---------------- Object-level Validation ----------------
    def validate(self, data):
        user = self.context["request"].user

        # fallback to instance values for partial updates
        make = data.get("make") or (self.instance.make if self.instance else None)
        model = data.get("model") or (self.instance.model if self.instance else None)
        make_ref = data.get("make_ref") or (self.instance.make_ref if self.instance else None)
        model_ref = data.get("model_ref") or (self.instance.model_ref if self.instance else None)
        dealer = data.get("dealer") or (self.instance.dealer if self.instance else None)
        broker = data.get("broker") or (self.instance.broker if self.instance else None)
        sale_type = data.get("sale_type") or (self.instance.sale_type if self.instance else None)
        price = data.get("price") or (self.instance.price if self.instance else None)
        auction_end = data.get("auction_end") or (self.instance.auction_end if self.instance else None)

        # Ensure at least one pair is provided
        if not (make and model) and not (make_ref and model_ref):
            raise serializers.ValidationError(
                "Either 'make' and 'model' or 'make_ref' and 'model_ref' must be provided."
            )

        # Auto-populate make/model from references
        if make_ref:
            data["make"] = make_ref.name
        if model_ref:
            data["model"] = model_ref.name

        # Ensure exactly one of dealer or broker
        if (dealer and broker) or (not dealer and not broker):
            raise serializers.ValidationError(
                "Exactly one of 'dealer' or 'broker' must be provided."
            )

        # Role-based validation
        if dealer and not has_role(user, ["super_admin", "admin", "dealer"]):
            raise serializers.ValidationError(
                "Only dealers, admins, or super admins can assign a dealer."
            )
        if broker and not has_role(user, ["super_admin", "admin", "broker"]):
            raise serializers.ValidationError(
                "Only brokers, admins, or super admins can assign a broker."
            )

        if dealer and dealer.user != user and not has_role(user, ["super_admin", "admin"]):
            raise serializers.ValidationError(
                "Only the dealer owner or admins can assign this dealer."
            )
        if broker and broker.profile.user != user and not has_role(user, ["super_admin", "admin"]):
            raise serializers.ValidationError(
                "Only the broker owner or admins can assign this broker."
            )

        # Auto-verify dealer cars if dealer is verified
        if dealer and dealer.is_verified:
            data["verification_status"] = "verified"
            data["priority"] = True

        # Auction logic
        if sale_type == "auction" and price is not None:
            raise serializers.ValidationError("Auction cars cannot have a fixed price.")
        if sale_type == "auction" and not auction_end:
            raise serializers.ValidationError("Auction end time is required for auction cars.")

        # Creation restrictions
        if self.instance is None and not has_role(
            user, ["super_admin", "admin", "dealer", "broker"]
        ):
            raise serializers.ValidationError(
                "Only brokers, dealers, admins, or super admins can create cars."
            )
        if self.instance and data.get("posted_by") and data["posted_by"] != user and not has_role(
            user, ["super_admin", "admin"]
        ):
            raise serializers.ValidationError(
                "Only the car owner or admins can update this car."
            )

        if make_ref and not CarMake.objects.filter(id=make_ref.id).exists():
            raise serializers.ValidationError("Selected make does not exist.")
        if model_ref and not CarModel.objects.filter(id=model_ref.id, make=make_ref).exists():
            raise serializers.ValidationError(
                "Selected model does not match the selected make."
            )

        return data

    # ---------------- Create & Update ----------------
    def create(self, validated_data):
        request = self.context["request"]

        # Extract uploaded_images from form-data
        uploaded_images_data = []
        for key, value in request.data.items():
            match = re.match(r"uploaded_images\[(\d+)\]\.(\w+)", key)
            if match:
                index, field = int(match.group(1)), match.group(2)
                while len(uploaded_images_data) <= index:
                    uploaded_images_data.append({})
                uploaded_images_data[index][field] = value

        validated_data.pop("uploaded_images", None)

        make_ref = validated_data.get("make_ref")
        model_ref = validated_data.get("model_ref")

        if make_ref and not validated_data.get("make"):
            validated_data["make"] = make_ref.name
        if model_ref and not validated_data.get("model"):
            validated_data["model"] = model_ref.name

        car = Car.objects.create(**validated_data)

        for index, img_data in enumerate(uploaded_images_data):
            img_data["car"] = car
            if "image_file" in img_data and isinstance(img_data["image_file"], str):
                file_key = f"uploaded_images[{index}].image_file"
                if file_key in request.FILES:
                    img_data["image_file"] = request.FILES[file_key]
            CarImageSerializer(context=self.context).create(img_data)

        return car

    def update(self, instance, validated_data):
        make_ref = validated_data.get("make_ref", instance.make_ref)
        model_ref = validated_data.get("model_ref", instance.model_ref)

        if make_ref:
            validated_data["make"] = make_ref.name
        if model_ref:
            validated_data["model"] = model_ref.name

        return super().update(instance, validated_data)

class FavoriteCarSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    car = serializers.PrimaryKeyRelatedField(queryset=Car.objects.all())
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = FavoriteCar
        fields = ['id', 'car', 'user', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def validate_car(self, value):
        # Ensure the car is available
        if not value.is_available:
            raise serializers.ValidationError("This car is not available to favorite.")
        return value

class CarViewSerializer(serializers.ModelSerializer):
    car_id = serializers.PrimaryKeyRelatedField(source='car', read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', read_only=True, allow_null=True)

    class Meta:
        model = CarView
        fields = ['id', 'car_id', 'user_id', 'ip_address', 'viewed_at']
        read_only_fields = ['viewed_at']

class CarViewAnalyticsSerializer(serializers.Serializer):
    car_id = serializers.IntegerField(source='car__id')
    car_make = serializers.CharField(source='car__make__name')
    total_views = serializers.IntegerField()

    def create(self, validated_data):
        # Automatically set the user to the authenticated user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

# ---------------- Verify Car Serializer ----------------
class VerifyCarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['verification_status']

    def validate_verification_status(self, value):
        valid_statuses = [choice[0] for choice in Car.VERIFICATION_STATUSES]
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_statuses:
            raise serializers.ValidationError(f"Verification status must be one of: {', '.join(valid_statuses)}.")
        return cleaned_value

    def validate(self, data):
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify cars.")
        return data
