from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from ..models import Car, CarImage, CarMake, CarModel, FavoriteCar, CarView
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.inventory.models import Contact
from online_car_market.bids.models import Bid
from django.contrib.auth import get_user_model
import re, bleach, logging
from datetime import datetime

logger = logging.getLogger(__name__)
User = get_user_model()

def has_any_role(user, roles):
    return user.is_authenticated and user.role in roles

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
        if self.context['request'].method in ['POST', 'PUT', 'PATCH']:
            user = self.context['request'].user
            if user.role not in ['admin', 'super_admin'] and not user.is_superuser:
                raise serializers.ValidationError(
                    "Only admins or super admins can create or update makes."
                )
        return data

class CarModelSerializer(serializers.ModelSerializer):
    make_id = serializers.IntegerField(source='make.id', read_only=True)
    make_name = serializers.CharField(source='make.name', read_only=True)

    class Meta:
        model = CarModel
        fields = ['id', 'name', 'make_id', 'make_name', 'make']
        extra_kwargs = {
            'make': {'write_only': True, 'required': True}
        }

    def get_make_name(self, obj):
        return obj.make.name if obj.make else None

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
        if self.context['request'].method in ['POST', 'PUT', 'PATCH']:
            user = self.context['request'].user
            if user.role not in ['admin', 'super_admin'] and not user.is_superuser:
                raise serializers.ValidationError(
                    "Only admins or super admins can create or update models."
                )
        return data

class CarImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField(read_only=True)
    image_file = serializers.ImageField(write_only=True, required=False)
    is_featured = serializers.BooleanField(required=False, default=False)
    caption = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = CarImage
        fields = '__all__'
        read_only_fields = ["id", "image_url", "uploaded_at"]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image_url(self, obj):
        try:
            return obj.image.url if obj.image else None
        except Exception as e:
            logger.error(f"Error fetching image_url for CarImage ID={obj.id}: {e}")
            return None

    def validate_caption(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned) > 255:
                raise serializers.ValidationError("Caption cannot exceed 255 characters.")
            return cleaned
        return value

    def validate_image_file(self, value):
        if value:
            max_size = 5 * 1024 * 1024
            if value.size > max_size:
                raise serializers.ValidationError("Image file size cannot exceed 5MB.")
            return value
        raise serializers.ValidationError("Image file is required.")

    def validate(self, data):
        user = self.context["request"].user
        car = data.get("car") or getattr(self.instance, "car", None)

        if self.instance is None:
            if user.role not in ["super_admin", "admin", "broker", "seller"]:
                raise serializers.ValidationError(
                    "Only sellers, brokers, admins, or super admins can create car images."
                )

            if car and user.role not in ["super_admin", "admin"] and getattr(car, "posted_by", None) != user:
                raise serializers.ValidationError(
                    "Only the car owner or admins can add images."
                )

        return data

    def create(self, validated_data):
        car = validated_data.pop("car", None)
        image_file = validated_data.pop("image_file", None)

        logger.debug(f"Creating CarImage with data: {validated_data} | image_file={image_file}")

        instance = CarImage(**validated_data)
        if car:
            instance.car = car
        if image_file:
            instance.image = image_file
        instance.save()

        logger.info(
            f"Saved CarImage ID={instance.id} | image={instance.image} | is_featured={instance.is_featured} | caption={instance.caption}")
        return instance

    def update(self, instance, validated_data):
        image_file = validated_data.pop("image_file", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if image_file:
            instance.image = image_file
        instance.save()
        return instance

class BidNestedSerializer(serializers.ModelSerializer):
    bidder = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = ["id", "bidder", "amount", "created_at"]

    def get_bidder(self, obj):
        user = obj.user
        profile = getattr(user, 'profile', None)

        if profile:
            first_name = profile.first_name
            last_name = profile.last_name
        else:
            first_name = None
            last_name = None

        return {
            "id": user.id,
            "first_name": first_name,
            "last_name": last_name,
        }

class CarMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ['id', 'make', 'model']

class CarListSerializer(serializers.ModelSerializer):
    featured_image = serializers.SerializerMethodField()
    seller = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = [
            "id", "make", "model", "year", "price", "mileage", "fuel_type",
            "drivetrain", "interior_color", "model_ref", "make_ref",
            "body_type", "sale_type", "status", "verification_status",
            "featured_image", "seller", "created_at",
        ]

    def get_featured_image(self, obj):
        images = list(obj.images.all())

        if not images:
            return None

        # Try to find featured image
        featured = next((img for img in images if img.is_featured), None)

        # If none marked as featured, use first image
        if not featured:
            featured = images[0]

        return featured.image.url

    def get_seller(self, obj):
        seller_obj = obj.dealer or obj.broker
        if not seller_obj:
            return None
        seller_type = "dealer" if obj.dealer else "broker"
        return {
            "type": seller_type,
            "id": seller_obj.id,
            "name": getattr(seller_obj, "get_display_name", lambda: None)(),
            "is_verified": getattr(seller_obj, "is_verified", None),
        }

class CarDetailSerializer(serializers.ModelSerializer):
    make = serializers.CharField(source="make_ref.name", read_only=True)
    model = serializers.CharField(source="model_ref.name", read_only=True)
    images = CarImageSerializer(many=True, read_only=True)  # all images
    bids = BidNestedSerializer(source="top_bids", many=True, read_only=True)  # top 10 bids
    seller = serializers.SerializerMethodField()
    bid_count = serializers.IntegerField(read_only=True)
    highest_bid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    seller_average_rating = serializers.FloatField(source="dealer_avg", read_only=True)
    features = serializers.SerializerMethodField()
    inspection = serializers.SerializerMethodField()

    class Meta:
        model = Car
        fields = [
            "id", "vin", "origin", "make", "model", "year", "price", "mileage", "fuel_type", "body_type", "interior_color",
            "exterior_color", "engine", "drivetrain", "condition", "trim", "description", "status", "sale_type", "auction_end",
            "dealer", "broker", "posted_by", "verification_status", "images", "bids", "seller", "bid_count", "highest_bid",
            "seller_average_rating", "features", "inspection", "created_at"
        ]

    def get_seller(self, obj):
        seller_obj = obj.dealer or obj.broker
        if not seller_obj:
            return None
        seller_type = "dealer" if obj.dealer else "broker"
        profile = getattr(seller_obj, "profile", None)
        user = getattr(profile, "user", None)

        return {
            "type": seller_type,
            "id": seller_obj.id,
            "name": getattr(seller_obj, "get_display_name", lambda: None)(),
            "email": user.email if user else None,
            "contact_number": getattr(profile, "contact", None),
            "is_verified": getattr(seller_obj, "is_verified", None),
        }

    def get_bids(self, obj):
        top_bids = getattr(obj, "top_bids", [])
        return [
            {
                "id": bid.id,
                "amount": bid.amount,
                "user_id": bid.user_id,
                "created_at": bid.created_at,
                "user_name": getattr(getattr(bid, "user", None), "username", None),
            }
            for bid in top_bids
        ]

    def get_features(self, obj):
        feature_fields = [
            "bluetooth",
            "heated_seats",
            "cd_player",
            "power_locks",
            "premium_wheels_rims",
            "winch", "alarm_anti_theft",
            "cooled_seats",
            "keyless_start",
            "body_kit",
            "navigation_system",
            "premium_lights",
            "cassette_player",
            "fog_lights",
            "leather_seats",
            "roof_rack",
            "dvd_player",
            "power_mirrors",
            "power_sunroof",
            "aux_audio_in",
            "brush_guard",
            "air_conditioning",
            "performance_tyres",
            "premium_sound_system",
            "heat", "vhs_player",
            "off_road_kit",
            "am_fm_radio",
            "moonroof",
            "racing_seats",
            "premium_paint",
            "spoiler",
            "power_windows",
            "sunroof",
            "climate_control",
            "parking_sensors",
            "rear_view_camera",
            "keyless_entry",
            "off_road_tyres",
            "satellite_radio",
            "power_seats",
            "tiptronic_gears",
            "dual_exhaust",
            "power_steering",
            "cruise_control",
            "all_wheel_steering",
            "front_airbags",
            "side_airbags",
            "n2o_system",
            "anti_lock_brakes",
        ]
        return [
            field.replace("_", " ").title()
            for field in feature_fields
            if getattr(obj, field, False)
        ]

    def get_inspection(self, obj):
        inspection = getattr(obj, "inspection", None)

        if not inspection:
            return None

        # Optional: only show verified inspections
        if inspection.status != "verified":
            return None

        return {
            "id": inspection.id,
            "status": inspection.status,
            "remarks": inspection.remarks,
            "inspection_date": inspection.inspection_date,
            "condition_status": inspection.condition_status,
            "verified_at": inspection.verified_at,
            "verified_by_email": getattr(inspection.verified_by, "email", None),
            "report_document": inspection.report_document.url if inspection.report_document else None,
        }

class CarWriteSerializer(serializers.ModelSerializer):
    dealer = serializers.PrimaryKeyRelatedField(read_only=True)
    broker = serializers.PrimaryKeyRelatedField(read_only=True)
    posted_by = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    make_ref = serializers.PrimaryKeyRelatedField(
        queryset=CarMake.objects.all(),
        required=False,
        allow_null=True
    )
    model_ref = serializers.PrimaryKeyRelatedField(
        queryset=CarModel.objects.all(),
        required=False,
        allow_null=True
    )
    images = CarImageSerializer(many=True, required=False)

    class Meta:
        model = Car
        exclude = [
            "id",
            "make",
            "model",
            "created_at",
            "updated_at",
            "sold_at",
            "verification_status",
            "priority",
        ]

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
            raise serializers.ValidationError(f"Year must be 1900-{current_year + 1}.")
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
            return cleaned
        return value

    def validate_interior_color(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
            return cleaned
        return value

    def validate_engine(self, value):
        if value:
            cleaned = bleach.clean(value.strip(), tags=[], strip=True)
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

    def validate_model_ref(self, value):
        make_ref_id = self.initial_data.get("make_ref")
        if value and make_ref_id and value.make.id != int(make_ref_id):
            raise serializers.ValidationError(
                "Selected model must belong to the selected make."
            )
        return value

    def validate(self, data):
        user = self.context["request"].user

        make = data.get("make") or getattr(self.instance, "make", None)
        model = data.get("model") or getattr(self.instance, "model", None)
        make_ref = data.get("make_ref") or getattr(self.instance, "make_ref", None)
        model_ref = data.get("model_ref") or getattr(self.instance, "model_ref", None)

        dealer = data.get("dealer")
        broker = data.get("broker")

        sale_type = data.get("sale_type") or getattr(self.instance, "sale_type", None)
        price = data.get("price") or getattr(self.instance, "price", None)
        auction_end = data.get("auction_end") or getattr(self.instance, "auction_end", None)

        # Make / Model Validation
        if not (make and model) and not (make_ref and model_ref):
            raise serializers.ValidationError(
                "Either 'make and model' or 'make_ref and model_ref' must be provided."
            )

        if make_ref:
            data["make"] = make_ref.name
        if model_ref:
            data["model"] = model_ref.name

        # ROLE-BASED Dealer/Broker Logic
        from online_car_market.dealers.models import DealerStaff

        seller_record = DealerStaff.objects.filter(user=user, role="seller").first()

        if user.role in ["admin", "super_admin"]:
            # Admin must provide one
            if (dealer and broker) or (not dealer and not broker):
                raise serializers.ValidationError(
                    "Admin must provide exactly one of 'dealer' or 'broker'."
                )

        elif user.role == "dealer":
            # Ignore input → force own dealer
            data["dealer"] = user.profile.dealer_profile
            data["broker"] = None

        elif user.role == "broker":
            # Ignore input → force own broker
            data["broker"] = user.profile.broker_profile
            data["dealer"] = None

        elif seller_record:
            # Seller → assign dealer automatically
            data["dealer"] = seller_record.dealer
            data["broker"] = None

        else:
            raise serializers.ValidationError("You are not allowed to create cars.")

        # Auction Rules
        if sale_type == "auction" and price is not None:
            raise serializers.ValidationError("Auction cars cannot have a fixed price.")

        if sale_type == "auction" and not auction_end:
            raise serializers.ValidationError("Auction end time is required.")

        # Update Permission Check
        if self.instance:
            car = self.instance

            is_admin = user.role in ["admin", "super_admin"]
            is_broker_owner = car.broker and car.broker.profile.user == user
            is_dealer_owner = car.dealer and car.dealer.profile.user == user

            is_seller_under_dealer = seller_record and car.dealer == seller_record.dealer

            if not (is_admin or is_broker_owner or is_dealer_owner or is_seller_under_dealer):
                raise serializers.ValidationError(
                    "You do not have permission to update this car."
                )

        return data

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        validated_data.pop("uploaded_images", None)

        dealer = None
        broker = None

        # ADMIN → can pass anything
        if user.role in ["admin", "super_admin"]:
            dealer = validated_data.get("dealer")
            broker = validated_data.get("broker")

        # DEALER → assign own dealer
        elif user.role == "dealer":
            dealer = user.profile.dealer_profile

        # SELLER → assign dealer automatically
        elif user.role == "seller":
            from online_car_market.dealers.models import DealerStaff

            staff = DealerStaff.objects.filter(user=user, role="seller").first()
            if not staff:
                raise serializers.ValidationError("Seller is not assigned to any dealer.")

            dealer = staff.dealer

        # BROKER → assign own broker
        elif user.role == "broker":
            broker = user.profile.broker_profile

        else:
            raise serializers.ValidationError("You are not allowed to create cars.")

        return Car.objects.create(
            dealer=dealer,
            broker=broker,
            posted_by=user,
            **validated_data
        )

    def update(self, instance, validated_data):
        validated_data.pop("uploaded_images", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

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
        if not value.status:
            raise serializers.ValidationError("This car is not available to favorite.")
        return value

    def create(self, validated_data):
        user = validated_data.pop("user")
        car = validated_data["car"]

        favorite, created = FavoriteCar.objects.update_or_create(
            user=user,
            car=car,
            defaults={"created_at": timezone.now()}
        )
        return favorite

class CarViewSerializer(serializers.ModelSerializer):
    car_id = serializers.PrimaryKeyRelatedField(source='car', queryset=Car.objects.all(), write_only=True)
    user_id = serializers.PrimaryKeyRelatedField(source='user', read_only=True)
    car = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = CarView
        fields = ['id', 'car_id', 'car', 'user_id', 'ip_address', 'viewed_at']
        read_only_fields = ['viewed_at', 'ip_address']

class CarVerificationListSerializer(serializers.ModelSerializer):
    dealer_name = serializers.CharField(source="dealer.profile.business_name", read_only=True)
    broker_name = serializers.CharField(source="broker.profile.business_name", read_only=True)
    posted_by = serializers.CharField(source="posted_by.email", read_only=True)

    class Meta:
        model = Car
        fields = [
            "id",
            "make",
            "model",
            "year",
            "price",
            "sale_type",
            "dealer_name",
            "broker_name",
            "posted_by",
            "verification_status",
            "priority",
            "created_at",
        ]

class CarVerificationAnalyticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pending = serializers.IntegerField()
    verified = serializers.IntegerField()
    rejected = serializers.IntegerField()

# Verify Car Serializer
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
        user = self.context["request"].user

        if user.role not in ["super_admin", "admin"]:
            raise serializers.ValidationError(
                "Only super admins or admins can verify cars."
            )

        return data

class ContactSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(required=True)
    recipient = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Contact
        fields = ['id', 'sender', 'recipient', 'message', 'phone', 'car', 'created_at']
        read_only_fields = ['id', 'sender', 'created_at']

    def validate_phone(self, value):
        if len(value) < 9:
            raise serializers.ValidationError("Invalid phone number.")
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user
        car = attrs.get("car")

        # Prevent duplicate contact per car
        if car and Contact.objects.filter(sender=user, car=car).exists():
            raise serializers.ValidationError(
                "You already contacted about this car."
            )

        return attrs
