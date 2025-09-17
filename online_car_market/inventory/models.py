from django.db import models
from cloudinary.models import CloudinaryField
from django.contrib.auth import get_user_model
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from django.utils.text import slugify

User = get_user_model()

class CarMake(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # slug = models.SlugField(max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Car Make'
        verbose_name_plural = 'Car Makes'

    ''' def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs) '''

    def __str__(self):
        return self.name


class CarModel(models.Model):
    make = models.ForeignKey(CarMake, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)
    # slug = models.SlugField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['make__name', 'name']
        verbose_name = 'Car Model'
        verbose_name_plural = 'Car Models'
        unique_together = ('make', 'name')

    ''' def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.make.name}-{self.name}")
        super().save(*args, **kwargs) '''

    def __str__(self):
        return f"{self.make.name} {self.name}"

class Car(models.Model):
    VERIFICATION_STATUSES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    BODY_TYPES = [
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('truck', 'Truck'),
        ('coupe', 'Coupe'),
        ('hatchback', 'Hatchback'),
        ('convertible', 'Convertible'),
        ('wagon', 'Wagon'),
        ('van', 'Van'),
        ('other', 'Other'),
    ]
    FUEL_TYPES = (
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
    )
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('pending_inspection', 'Pending Inspection'),
        ('under_maintenance', 'Under Maintenance'),
        ('delivered', 'Delivered'),
        ('archived', 'Archived'),
    ]
    SALE_TYPES = (
        ('fixed_price', 'Fixed Price'),
        ('auction', 'Auction'),
    )

    DRIVETRAIN_TYPES = [
        ('fwd', 'Front-Wheel Drive'),
        ('rwd', 'Rear-Wheel Drive'),
        ('awd', 'All-Wheel Drive'),
        ('4wd', 'Four-Wheel Drive'),
    ]

    CONDITIONS = [
        ('new', 'New'),
        ('used', 'Used'),
    ]

    # core fields
    make = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    model = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    make_ref = models.ForeignKey(CarMake, on_delete=models.SET_NULL, null=True, blank=True, related_name='cars', db_index=True)
    model_ref = models.ForeignKey(CarModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='cars', db_index=True)
    year = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, db_index=True)
    mileage = models.IntegerField()
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPES, db_index=True)
    body_type = models.CharField(max_length=20, choices=BODY_TYPES, default='sedan', db_index=True)
    exterior_color = models.CharField(max_length=20, default='white')
    interior_color = models.CharField(max_length=20,  default='white')
    engine = models.CharField(max_length=100, null=True, blank=True)
    drivetrain = models.CharField(max_length=20, choices=DRIVETRAIN_TYPES, default='fwd', db_index=True)
    condition = models.CharField(max_length=20, choices=CONDITIONS, default='new')
    trim = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='available')
    sale_type = models.CharField(max_length=20, choices=SALE_TYPES, default='fixed_price')
    auction_end = models.DateTimeField(null=True, blank=True)
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='cars')
    broker = models.ForeignKey(BrokerProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='cars')
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_cars', db_index=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUSES, default='pending')
    priority = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    def save(self, *args, **kwargs):
        if self.make_ref and not self.make:
            self.make = self.make_ref.name
        if self.model_ref and not self.model:
            self.model = self.model_ref.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.make} {self.model} ({self.year}) - {self.BODY_TYPES}"

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(dealer__isnull=False) | models.Q(broker__isnull=False),
                name='dealer_or_broker_required'
            )
        ]
        ordering = ['make', 'model', 'year']
        verbose_name = 'Car'
        verbose_name_plural = 'Cars'

class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image')  # stores the Cloudinary image reference
    is_featured = models.BooleanField(default=False)
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

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
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # for anonymous users
    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user or self.ip_address} viewed {self.car}"



