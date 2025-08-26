from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from rolepermissions.checkers import has_role
from ..models import Car, CarImage, Bid, Payment, CarMake, CarModel
from online_car_market.dealers.models import Dealer
from django.contrib.auth import get_user_model
import re
import bleach
from datetime import datetime
from django.utils import timezone

User = get_user_model()

# ---------------- CarImage Serializer ----------------
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
            if not has_role(user, ["super_admin", "admin", "dealer"]):
                raise serializers.ValidationError("Only dealers, admins, or super admins can create car images.")
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

class BidSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault())

    class Meta:
        model = Bid
        fields = ['id', 'car', 'user', 'amount', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Bid amount must be positive.")
        return value

    def validate_car(self, value):
        if value.sale_type != 'auction':
            raise serializers.ValidationError("Bids can only be placed on auction cars.")
        if value.auction_end and value.auction_end < timezone.now():
            raise serializers.ValidationError("Auction has ended.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        car = data.get('car')
        if car.posted_by == user:
            raise serializers.ValidationError("You cannot bid on your own car.")
        return data

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'user', 'car', 'amount', 'payment_type', 'is_confirmed', 'transaction_id', 'created_at']
        read_only_fields = ['id', 'user', 'is_confirmed', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be positive.")
        return value

    def validate_payment_type(self, value):
        valid_types = [choice[0] for choice in Payment.PAYMENT_TYPES]
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_types:
            raise serializers.ValidationError(f"Payment type must be one of: {', '.join(valid_types)}.")
        return cleaned_value

    def validate_transaction_id(self, value):
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if not re.match(r'^[a-zA-Z0-9-]+$', cleaned_value):
            raise serializers.ValidationError("Transaction ID can only contain letters, numbers, or hyphens.")
        return cleaned_value

    def validate(self, data):
        user = self.context['request'].user
        payment_type = data.get('payment_type')
        car = data.get('car')
        if payment_type == 'listing_fee' and not has_role(user, 'broker'):
            raise serializers.ValidationError("Only brokers can pay listing fees.")
        if payment_type in ['commission', 'purchase'] and not car:
            raise serializers.ValidationError("Car is required for commission or purchase payments.")
        return data

class CarSerializer(serializers.ModelSerializer):
    dealer = serializers.PrimaryKeyRelatedField(queryset=Dealer.objects.all())
    posted_by = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault())
    images = CarImageSerializer(many=True, read_only=True)
    uploaded_images = CarImageSerializer(many=True, write_only=True, required=False)
    bids = BidSerializer(many=True, read_only=True)
    verification_status = serializers.ChoiceField(choices=Car.VERIFICATION_STATUSES, read_only=True)
    make_ref = serializers.PrimaryKeyRelatedField(queryset=CarMake.objects.all(), required=False, allow_null=True)
    model_ref = serializers.PrimaryKeyRelatedField(queryset=CarModel.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Car
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'verification_status']

    # ---------------- Field Validations ----------------
    def validate_make(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        ''' if not cleaned:
            raise serializers.ValidationError("Make is required.") '''
        if len(cleaned) > 100:
            raise serializers.ValidationError("Make cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', cleaned):
            raise serializers.ValidationError("Invalid characters.")
        return cleaned

    def validate_model(self, value):
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        ''' if not cleaned:
            raise serializers.ValidationError("Model is required.") '''
        if len(cleaned) > 100:
            raise serializers.ValidationError("Model cannot exceed 100 characters.")
        if not re.match(r'^[a-zA-Z0-9\s-]+$', cleaned):
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

    def validate_fuel_type(self, value):
        valid_types = ['electric', 'hybrid', 'petrol', 'diesel']
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned not in valid_types:
            raise serializers.ValidationError(f"Fuel type must be one of: {', '.join(valid_types)}.")
        return cleaned

    def validate_status(self, value):
        valid_statuses = [c[0] for c in Car.STATUS_CHOICES]
        cleaned = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned not in valid_statuses:
            raise serializers.ValidationError(f"Status must be one of: {', '.join(valid_statuses)}.")
        return cleaned

    def validate_sale_type(self, value):
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        valid_types = [choice[0] for choice in Car.SALE_TYPES]
        if cleaned_value not in valid_types:
            raise serializers.ValidationError(f"Sale type must be one of: {', '.join(valid_types)}.")
        return cleaned_value

    def validate_auction_end(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Auction end time must be in the future.")
        return value

    def validate_dealer(self, value):
        if not has_role(value.user, 'dealer'):
            raise serializers.ValidationError("Dealer user must have dealer role.")
        user = self.context['request'].user
        if value.user != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only dealer owner or admins can assign this dealer.")
        return value

    def validate_model_ref(self, value):
        if value and value.make != self.initial_data.get('make_ref'):
            raise serializers.ValidationError("Selected model must belong to the selected make.")
        return value

    def validate(self, data):
        user = self.context['request'].user
        sale_type = data.get('sale_type')
        price = data.get('price')
        auction_end = data.get('auction_end')
        make = data.get('make')
        model = data.get('model')
        make_ref = data.get('make_ref')
        model_ref = data.get('model_ref')

        # Ensure at least one pair is provided
        if not (make and model) and not (make_ref and model_ref):
            raise serializers.ValidationError(
                "Either 'make' and 'model' or 'make_ref' and 'model_ref' must be provided.")

        # Auto-populate make and model from references if provided
        if make_ref:
            data['make'] = make_ref.name
        if model_ref:
            data['model'] = model_ref.name

        if sale_type == 'auction' and price is not None:
            raise serializers.ValidationError("Auction cars cannot have a fixed price.")
        if sale_type == 'auction' and not auction_end:
            raise serializers.ValidationError("Auction end time is required for auction cars.")
        if self.instance is None and not has_role(user, ['super_admin', 'admin', 'dealer']):
            raise serializers.ValidationError("Only dealers, admins, or super admins can create cars.")
        if self.instance and data.get('posted_by') and data['posted_by'] != user and not has_role(user, ['super_admin', 'admin']):
            raise serializers.ValidationError("Only the car owner or admins can update this car.")

        if make_ref and not CarMake.objects.filter(id=make_ref.id).exists():
            raise serializers.ValidationError("Selected make does not exist.")
        if model_ref and not CarModel.objects.filter(id=model_ref.id, make=make_ref).exists():
            raise serializers.ValidationError("Selected model does not match the selected make.")
        return data

    # ---------------- Create method ----------------
    def create(self, validated_data):
        make_ref = validated_data.get('make_ref')
        model_ref = validated_data.get('model_ref')

        # Auto-populate make/model from refs
        if make_ref:
            validated_data['make'] = make_ref.name
        if model_ref:
            validated_data['model'] = model_ref.name
            
        request = self.context['request']
        # print("Request data:", dict(request.data))

        # Extract uploaded_images from form-data
        uploaded_images_data = []
        for key, value in request.data.items():
            match = re.match(r'uploaded_images\[(\d+)\]\.(\w+)', key)
            if match:
                index, field = int(match.group(1)), match.group(2)
                while len(uploaded_images_data) <= index:
                    uploaded_images_data.append({})
                uploaded_images_data[index][field] = value

        # Remove uploaded_images fields from validated_data before creating Car
        # (Django model does not have these fields)
        validated_data.pop('uploaded_images', None)

        # Create Car instance
        car = Car.objects.create(**validated_data)

        # Create CarImage instances
        for img_data in uploaded_images_data:
            img_data['car'] = car
            # For uploaded files, use request.FILES
            if 'image_file' in img_data:
                if isinstance(img_data['image_file'], str):
                    # replace the string from request.data with actual UploadedFile
                    file_key = None
                    for k, v in request.FILES.items():
                        if k.startswith(f"uploaded_images[{uploaded_images_data.index(img_data)}].image_file"):
                            file_key = k
                            break
                    if file_key:
                        img_data['image_file'] = request.FILES[file_key]
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
