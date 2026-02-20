from django.utils import timezone
from django.db.models import Avg, Max, Count
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from rolepermissions.checkers import has_role
from ..models import Car, CarImage, CarMake, CarModel, FavoriteCar, CarView
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.users.models import Profile
from online_car_market.bids.models import Bid
from django.contrib.auth import get_user_model
import re, bleach, logging
from datetime import datetime

logger = logging.getLogger(__name__)
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
    image_file = serializers.ImageField(write_only=True, required=False)
    is_featured = serializers.BooleanField(required=False, default=False)
    caption = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = CarImage
        # fields = ["id", "image_file", "image_url", "is_featured", "caption", "uploaded_at"]
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
            if not has_role(user, ["super_admin", "admin", "broker", 'seller']):
                raise serializers.ValidationError("Only sellers, brokers, admins, or super admins can create car images.")
            if car and not has_role(user, ["super_admin", "admin"]) and getattr(car, "posted_by", None) != user:
                raise serializers.ValidationError("Only the car owner or admins can add images.")
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
        # Use the prefetch attribute from queryset
        images = getattr(obj, "featured_images", [])
        if images:
            # Always take the first one (featured)
            return images[0].image.url
        return None

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
    images = CarImageSerializer(many=True, read_only=True)  # all images
    bids = BidNestedSerializer(source="top_bids", many=True, read_only=True)  # top 10 bids
    seller = serializers.SerializerMethodField()
    bid_count = serializers.IntegerField(read_only=True)
    highest_bid = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    seller_average_rating = serializers.FloatField(source="dealer_avg", read_only=True)

    class Meta:
        model = Car
        exclude = ["dealer", "broker"]

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

class CarWriteSerializer(serializers.ModelSerializer):
    dealer = serializers.PrimaryKeyRelatedField(
        queryset=DealerProfile.objects.all(),
        required=False,
        allow_null=True
    )
    broker = serializers.PrimaryKeyRelatedField(
        queryset=BrokerProfile.objects.all(),
        required=False,
        allow_null=True
    )
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

    class Meta:
        model = Car
        exclude = [
            "id",
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
        user = self.context["request"].user

        # Validate that the provided dealer actually belongs to a dealer role
        if value and not has_role(value.profile.user, "dealer"):
            raise serializers.ValidationError("Dealer user must have a dealer role.")

        # Allow sellers under the dealer
        if has_role(user, "seller"):
            from online_car_market.dealers.models import DealerStaff
            staff = DealerStaff.objects.filter(user=user, dealer=value, role="seller").first()
            if not staff:
                raise serializers.ValidationError(
                    "You are not assigned as a seller under this dealer."
                )
            return value  # valid for assigned sellers

        # Allow dealer owner
        if value and value.profile.user == user:
            return value

        # Allow admins/super_admins
        if has_role(user, ["super_admin", "admin"]):
            return value

        # Otherwise, block access
        raise serializers.ValidationError(
            "Only assigned sellers, dealer owner, or admins can assign this dealer."
        )

    def validate_broker(self, value):
        if value and not has_role(value.profile.user, "broker"):
            raise serializers.ValidationError("Broker user must have broker role.")
        user = self.context["request"].user
        if value and value.profile.user != user and not has_role(user, ["super_admin", "admin"]):
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

    def validate(self, data):
        user = self.context["request"].user
        make = data.get("make") or getattr(self.instance, "make", None)
        model = data.get("model") or getattr(self.instance, "model", None)
        make_ref = data.get("make_ref") or getattr(self.instance, "make_ref", None)
        model_ref = data.get("model_ref") or getattr(self.instance, "model_ref", None)
        dealer = data.get("dealer") or getattr(self.instance, "dealer", None)
        broker = data.get("broker") or getattr(self.instance, "broker", None)
        sale_type = data.get("sale_type") or getattr(self.instance, "sale_type", None)
        price = data.get("price") or getattr(self.instance, "price", None)
        auction_end = data.get("auction_end") or getattr(self.instance, "auction_end", None)

        # Validate make/model
        if not (make and model) and not (make_ref and model_ref):
            raise serializers.ValidationError(
                "Either 'make' and 'model' or 'make_ref' and 'model_ref' must be provided."
            )

        if make_ref:
            data["make"] = make_ref.name
        if model_ref:
            data["model"] = model_ref.name

        # Dealer/Broker consistency
        final_dealer = dealer if "dealer" in data else getattr(self.instance, "dealer", None)
        final_broker = broker if "broker" in data else getattr(self.instance, "broker", None)

        if (final_dealer and final_broker) or (not final_dealer and not final_broker):
            raise serializers.ValidationError("Exactly one of 'dealer' or 'broker' must be provided.")

        # ---------------- Dealer validation ----------------
        if dealer:
            from online_car_market.dealers.models import DealerStaff
            if has_role(user, "seller"):
                # Seller must be under this dealer
                if not DealerStaff.objects.filter(user=user, dealer=dealer, role="seller").exists():
                    raise serializers.ValidationError("You must be a seller under this dealer to post a car.")
            elif has_role(user, "dealer"):
                if dealer.profile.user != user:
                    raise serializers.ValidationError("Dealers can only assign themselves.")
            elif not has_role(user, ["super_admin", "admin"]):
                raise serializers.ValidationError("Permission denied.")

        # Broker validation
        if broker:
            if broker.profile.user != user and not has_role(user, ["super_admin", "admin"]):
                raise serializers.ValidationError("Only the broker owner or admins can assign this broker.")

        # Auction rules
        if sale_type == "auction" and price is not None:
            raise serializers.ValidationError("Auction cars cannot have a fixed price.")
        if sale_type == "auction" and not auction_end:
            raise serializers.ValidationError("Auction end time is required for auction cars.")

        # Role permission
        if self.instance is None:
            if has_role(user, "seller"):
                from online_car_market.dealers.models import DealerStaff
                if not DealerStaff.objects.filter(user=user, role="seller").exists():
                    raise serializers.ValidationError("Seller must be assigned to a dealer to post cars.")
            elif not has_role(user, ["super_admin", "admin", "dealer", "broker", "seller"]):
                raise serializers.ValidationError(
                    "Only dealers, brokers, sellers, admins, or super admins can create cars.")

        # Ownership rule for update
        if self.instance and data.get("posted_by") and data["posted_by"] != user and not has_role(user, ["super_admin",
                                                                                                         "admin"]):
            raise serializers.ValidationError("Only the car owner or admins can update this car.")

        # Verification status rules
        if self.instance is None:  # creation case only
            if has_role(user, ["super_admin", "admin"]):
                data["verification_status"] = "verified"
                data["priority"] = True
            else:
                data["verification_status"] = "pending"
                data["priority"] = False

        return data

    def create(self, validated_data):
        request = self.context["request"]

        # Auto-assign dealer for sellers
        if has_role(request.user, "seller"):
            from online_car_market.dealers.models import DealerStaff
            staff = DealerStaff.objects.filter(user=request.user, role="seller").first()
            if staff and not validated_data.get("dealer"):
                validated_data["dealer"] = staff.dealer

        validated_data.pop("uploaded_images", None)
        car = Car.objects.create(**validated_data)
        return car

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
        user = self.context["request"].user
        car = validated_data["car"]

        # Use update_or_create to avoid duplicates
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
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only super admins or admins can verify cars.")
        return data

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'first_name', 'last_name', 'contact', 'address', 'image', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Convert CloudinaryField image to URL if it exists
        if instance.image and hasattr(instance.image, 'url'):
            representation['image'] = instance.image.url
        return representation
