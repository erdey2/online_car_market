from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone
from cloudinary.models import CloudinaryField
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.users.models import Profile

User = get_user_model()

class CarMake(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Car Make"
        verbose_name_plural = "Car Makes"

    def __str__(self):
        return self.name

class CarModel(models.Model):
    make = models.ForeignKey(CarMake, on_delete=models.CASCADE, related_name="models", db_index=True)
    name = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "make__name",
            "name"
        ]
        verbose_name = "Car Model"
        verbose_name_plural = "Car Models"

        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                "make",
                name="unique_model_per_make"
            )
        ]

    def __str__(self):
        return self.name

class CarMakeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    requested_name = models.CharField(max_length=100, db_index=True)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="car_make_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default="pending", db_index=True)

    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_make_requests")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "status"
                ]
            ),
            models.Index(
                fields=[
                    "requested_by"
                ]
            ),
            models.Index(
                fields=[
                    "created_at"
                ]
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                Lower("requested_name"),
                "status",
                condition=models.Q(
                    status="pending"
                ),
                name="unique_pending_make_request"
            )
        ]

    def __str__(self):
        return f"{self.requested_name} ({self.status})"

class CarModelRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    make = models.ForeignKey(CarMake, on_delete=models.CASCADE, related_name="model_requests", db_index=True)
    requested_name = models.CharField(max_length=100, db_index=True)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="car_model_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default="pending", db_index=True)

    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_model_requests")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = [
            "-created_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "status"
                ]
            ),
            models.Index(
                fields=[
                    "requested_by"
                ]
            ),
            models.Index(
                fields=[
                    "make"
                ]
            ),
            models.Index(
                fields=[
                    "created_at"
                ]
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                Lower("requested_name"),
                "make",
                "status",
                condition=models.Q(
                    status="pending"
                ),
                name="unique_pending_model_request"
            )
        ]


    def __str__(self):
        return (
            f"{self.make.name} "
            f"{self.requested_name} "
            f"({self.status})"
        )

class Car(models.Model):
    VERIFICATION_STATUSES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]
    BODY_TYPES = [
        ("sedan", "Sedan"),
        ("suv", "SUV"),
        ("truck", "Truck"),
        ("coupe", "Coupe"),
        ("hatchback", "Hatchback"),
        ("convertible", "Convertible"),
        ("wagon", "Wagon"),
        ("van", "Van"),
        ("other", "Other"),
    ]
    FUEL_TYPES = (
        ("electric", "Electric"),
        ("hybrid", "Hybrid"),
        ("petrol", "Petrol"),
        ("diesel", "Diesel"),
    )
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("available", "Available"),
        ("reserved", "Reserved"),
        ("sold", "Sold"),
        ("pending_inspection", "Pending Inspection"),
        ("under_maintenance", "Under Maintenance"),
        ("delivered", "Delivered"),
        ("archived", "Archived"),
    ]
    SALE_TYPES = (
        ("fixed_price", "Fixed Price"),
        ("auction", "Auction"),
    )
    DRIVETRAIN_TYPES = [
        ("fwd", "Front-Wheel Drive"),
        ("rwd", "Rear-Wheel Drive"),
        ("awd", "All-Wheel Drive"),
        ("4wd", "Four-Wheel Drive"),
    ]
    CONDITIONS = [
        ("new", "New"),
        ("used", "Used"),
    ]

    # Basic Vehicle Information
    vin = models.CharField(max_length=17, unique=True, null=True, blank=True, db_index=True)
    origin = models.CharField(max_length=100, null=True, blank=True)

    # Legacy text fields
    # kept for search compatibility
    make = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    model = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    # Approved Make / Model
    make_ref = models.ForeignKey(CarMake, null=True, blank=True, on_delete=models.SET_NULL, related_name="cars", db_index=True)
    model_ref = models.ForeignKey(CarModel, null=True, blank=True, on_delete=models.SET_NULL, related_name="cars", db_index=True)

    # Pending Requests
    pending_make_request = models.ForeignKey(CarMakeRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="draft_cars", db_index=True)
    pending_model_request = models.ForeignKey(CarModelRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name="draft_cars", db_index=True)

    year = models.IntegerField(db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, db_index=True)
    mileage = models.IntegerField(db_index=True)
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPES, db_index=True)
    body_type = models.CharField(max_length=20, choices=BODY_TYPES, default="sedan", db_index=True)
    exterior_color = models.CharField(max_length=20, default="white")
    interior_color = models.CharField(max_length=20, default="white")
    engine = models.CharField(max_length=100, null=True, blank=True)
    drivetrain = models.CharField(max_length=20, choices=DRIVETRAIN_TYPES, default="fwd", db_index=True)
    condition = models.CharField(max_length=20, choices=CONDITIONS, default="new")
    trim = models.CharField(max_length=50, null=True, blank=True)

    description = models.TextField(null=True, blank=True)

    # Sale Information
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft", db_index=True)
    sale_type = models.CharField(max_length=20, choices=SALE_TYPES, default="fixed_price")
    auction_end = models.DateTimeField(null=True, blank=True)

    # Ownership
    dealer = models.ForeignKey(DealerProfile, null=True, blank=True, on_delete=models.CASCADE, related_name="cars")
    broker = models.ForeignKey(BrokerProfile, null=True, blank=True, on_delete=models.CASCADE, related_name="cars")
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posted_cars", db_index=True)

    # Verification
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUSES, default="pending", db_index=True)
    priority = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    sold_at = models.DateTimeField(null=True, blank=True, db_index=True)

    views_count = models.IntegerField(default=0, db_index=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_cars")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Extra
    bluetooth = models.BooleanField(default=False)
    heated_seats = models.BooleanField(default=False)
    cd_player = models.BooleanField(default=False)
    power_locks = models.BooleanField(default=False)
    premium_wheels_rims = models.BooleanField(default=False)
    winch = models.BooleanField(default=False)
    alarm_anti_theft = models.BooleanField(default=False)
    cooled_seats = models.BooleanField(default=False)
    keyless_start = models.BooleanField(default=False)
    body_kit = models.BooleanField(default=False)
    navigation_system = models.BooleanField(default=False)
    premium_lights = models.BooleanField(default=False)
    cassette_player = models.BooleanField(default=False)
    fog_lights = models.BooleanField(default=False)
    leather_seats = models.BooleanField(default=False)
    roof_rack = models.BooleanField(default=False)
    dvd_player = models.BooleanField(default=False)
    power_mirrors = models.BooleanField(default=False)
    power_sunroof = models.BooleanField(default=False)
    aux_audio_in = models.BooleanField(default=False)
    brush_guard = models.BooleanField(default=False)
    air_conditioning = models.BooleanField(default=False)
    performance_tyres = models.BooleanField(default=False)
    premium_sound_system = models.BooleanField(default=False)
    heat = models.BooleanField(default=False)
    vhs_player = models.BooleanField(default=False)
    off_road_kit = models.BooleanField(default=False)
    am_fm_radio = models.BooleanField(default=False)
    moonroof = models.BooleanField(default=False)
    racing_seats = models.BooleanField(default=False)
    premium_paint = models.BooleanField(default=False)
    spoiler = models.BooleanField(default=False)
    power_windows = models.BooleanField(default=False)
    sunroof = models.BooleanField(default=False)
    climate_control = models.BooleanField(default=False)
    parking_sensors = models.BooleanField(default=False)
    rear_view_camera = models.BooleanField(default=False)
    keyless_entry = models.BooleanField(default=False)
    off_road_tyres = models.BooleanField(default=False)
    satellite_radio = models.BooleanField(default=False)
    power_seats = models.BooleanField(default=False)

    # Technical Features (Boolean)
    tiptronic_gears = models.BooleanField(default=False)
    dual_exhaust = models.BooleanField(default=False)
    power_steering = models.BooleanField(default=False)
    cruise_control = models.BooleanField(default=False)
    all_wheel_steering = models.BooleanField(default=False)
    front_airbags = models.BooleanField(default=False)
    side_airbags = models.BooleanField(default=False)
    n2o_system = models.BooleanField(default=False)
    anti_lock_brakes = models.BooleanField(default=False)

    def __str__(self):

        make = (
            self.make
            or self.make_ref.name
            if self.make_ref
            else "Unknown"
        )

        model = (
            self.model
            or self.model_ref.name
            if self.model_ref
            else "Unknown"
        )

        return f"{make} {model} ({self.year})"

    # Validation
    def clean(self):

        # Model must belong to selected make
        if (
            self.make_ref
            and self.model_ref
            and self.model_ref.make_id != self.make_ref.id
        ):
            raise ValidationError(
                {
                    "model_ref":
                        "Selected model does not belong to selected make."
                }
            )

        # Cannot have approved make and pending make request
        if (
            self.make_ref
            and self.pending_make_request
        ):
            raise ValidationError(
                {
                    "pending_make_request":
                        "A car cannot have both approved make and pending make request."
                }
            )
        # Cannot have approved model and pending model request
        if (
            self.model_ref
            and self.pending_model_request
        ):
            raise ValidationError(
                {
                    "pending_model_request":
                        "A car cannot have both approved model and pending model request."
                }
            )

    # Save
    def save(self, *args, **kwargs):

        self.full_clean()

        # Sync approved taxonomy
        if self.make_ref:
            self.make = self.make_ref.name
            self.pending_make_request = None

        else:
            self.make = None

        if self.model_ref:
            self.model = self.model_ref.name
            self.pending_model_request = None

        else:
            self.model = None

        # Automatically record sold date
        if (
            self.status == "sold"
            and not self.sold_at
        ):
            self.sold_at = timezone.now()

        super().save(*args, **kwargs)

    # Draft Workflow Helpers
    @property
    def waiting_for_make(self):

        return (
            self.make_ref_id is None
            and self.pending_make_request_id is not None
        )

    @property
    def waiting_for_model(self):

        return (
            self.model_ref_id is None
            and self.pending_model_request_id is not None
        )

    @property
    def is_waiting_for_taxonomy(self):

        return (
            self.waiting_for_make
            or self.waiting_for_model
        )

    class Meta:

        ordering = [
            "-created_at"
        ]

        verbose_name = "Car"
        verbose_name_plural = "Cars"

        indexes = [

            models.Index(
                fields=[
                    "verification_status"
                ]
            ),

            models.Index(
                fields=[
                    "status"
                ]
            ),

            models.Index(
                fields=[
                    "created_at"
                ]
            ),

            models.Index(
                fields=[
                    "dealer"
                ]
            ),

            models.Index(
                fields=[
                    "broker"
                ]
            ),

            models.Index(
                fields=[
                    "make_ref"
                ]
            ),

            models.Index(
                fields=[
                    "model_ref"
                ]
            ),

            models.Index(
                fields=[
                    "pending_make_request"
                ]
            ),

            models.Index(
                fields=[
                    "pending_model_request"
                ]
            ),
        ]

        constraints = [

            # Either dealer or broker, never both
            models.CheckConstraint(
                check=(
                    models.Q(
                        dealer__isnull=False,
                        broker__isnull=True
                    )
                    |
                    models.Q(
                        dealer__isnull=True,
                        broker__isnull=False
                    )
                ),
                name="exactly_one_of_dealer_or_broker"
            ),

            # Cannot have approved make and pending make request
            models.CheckConstraint(
                check=(
                    models.Q(
                        make_ref__isnull=True
                    )
                    |
                    models.Q(
                        pending_make_request__isnull=True
                    )
                ),
                name="no_make_and_pending_make"
            ),

            # Cannot have approved model and pending model request
            models.CheckConstraint(
                check=(
                    models.Q(
                        model_ref__isnull=True
                    )
                    |
                    models.Q(
                        pending_model_request__isnull=True
                    )
                ),
                name="no_model_and_pending_model"
            ),
        ]

class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image')  # stores the Cloudinary image reference
    is_featured = models.BooleanField(default=False)
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["car"],
                condition=models.Q(is_featured=True),
                name="unique_featured_image_per_car"
            )
        ]

    def __str__(self):
        return f"Image for {self.car} (Featured: {self.is_featured})"

    def save(self, *args, **kwargs):
        if self.is_featured:
            # Set is_featured=False for all other images of this car
            CarImage.objects.filter(car=self.car, is_featured=True).exclude(pk=self.pk).update(is_featured=False)
        super().save(*args, **kwargs)

class FavoriteCar(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_cars')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'car')  # Prevent duplicate favorites
        verbose_name = 'Favorite Car'
        verbose_name_plural = 'Favorite Cars'

    def __str__(self):
        return f"{self.user.email} favors {self.car}"

class CarView(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="car_views")
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # for anonymous users
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["car", "user"],
                condition=Q(user__isnull=False),
                name="unique_car_user_view"
            ),
            models.UniqueConstraint(
                fields=["car", "ip_address"],
                condition=Q(user__isnull=True),
                name="unique_car_ip_view"
            ),
        ]
        indexes = [
            models.Index(fields=["viewed_at"]),
            models.Index(fields=["car", "viewed_at"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user or self.ip_address} viewed {self.car}"

class Contact(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_contacts")
    recipient = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="received_contacts")
    phone = models.CharField(max_length=20)
    message = models.TextField(blank=True, null=True)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
