from django.contrib import admin
from django.contrib.auth import get_user_model
from rolepermissions.admin import RolePermissionsUserAdmin
from rolepermissions.roles import get_user_roles, assign_role, remove_role
from rolepermissions.exceptions import RoleDoesNotExist
from online_car_market.users.models import Profile
from online_car_market.buyers.models import BuyerProfile, LoyaltyProgram
from online_car_market.dealers.models import DealerProfile, DealerRating
from online_car_market.brokers.models import BrokerProfile, BrokerRating
from online_car_market.inventory.models import Car, CarImage
from django.utils.html import format_html
from rolepermissions.checkers import has_role
from django.db.models import Count

User = get_user_model()

# Unregister User first
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


# Inline for Profile under User
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['first_name', 'last_name', 'contact', 'address', 'image', 'image_preview', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at', 'image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" />', obj.image.url)
        return "No image"

    image_preview.short_description = "Image Preview"


# Inline for BuyerProfile under Profile
class BuyerProfileInline(admin.StackedInline):
    model = BuyerProfile
    can_delete = False
    verbose_name_plural = 'Buyer Profile'
    fields = []
    readonly_fields = ['loyalty_points']


# Inline for DealerProfile under Profile
class DealerProfileInline(admin.StackedInline):
    model = DealerProfile
    can_delete = False
    verbose_name_plural = 'Dealer Profile'
    fields = ['company_name', 'license_number', 'tax_id', 'telebirr_account', 'is_verified']
    readonly_fields = ['is_verified']


# Inline for BrokerProfile under Profile
class BrokerProfileInline(admin.StackedInline):
    model = BrokerProfile
    can_delete = False
    verbose_name_plural = 'Broker Profile'
    fields = ['national_id', 'telebirr_account', 'is_verified']
    readonly_fields = ['is_verified']


# Custom User Admin
@admin.register(User)
class CustomUserAdmin(RolePermissionsUserAdmin):
    ordering = ("email",)
    list_display = ("email", "is_active", "is_staff", "get_roles")
    search_fields = ("email",)
    list_filter = ("is_active", "is_staff")
    inlines = [ProfileInline]
    actions = ['assign_buyer_role', 'assign_dealer_role', 'assign_broker_role', 'assign_admin_role',
               'assign_superadmin_role']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('description',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'description', 'is_active', 'is_staff'),
        }),
    )

    def get_roles(self, obj):
        return ", ".join([role.get_name() for role in get_user_roles(obj)])

    get_roles.short_description = "Roles"

    def _assign_role(self, request, queryset, role_name):
        if not has_role(request.user, ['super_admin', 'admin']) and not request.user.is_superuser:
            self.message_user(request, "Only super admins or admins can assign roles.", level='error')
            return
        for user in queryset:
            try:
                current_roles = [role.get_name() for role in get_user_roles(user)]
                for role in current_roles:
                    try:
                        remove_role(user, role)
                    except RoleDoesNotExist:
                        self.message_user(request, f"Role {role} does not exist for {user.email}.", level='warning')
                assign_role(user, role_name)
                Profile.objects.get_or_create(user=user)
                if role_name == 'buyer':
                    BuyerProfile.objects.get_or_create(profile=Profile.objects.get(user=user))
                elif role_name == 'dealer':
                    DealerProfile.objects.get_or_create(
                        profile=Profile.objects.get(user=user),
                        defaults={'company_name': user.email, 'license_number': '', 'telebirr_account': ''}
                    )
                elif role_name == 'broker':
                    BrokerProfile.objects.get_or_create(
                        profile=Profile.objects.get(user=user),
                        defaults={'national_id': f"ID_{user.id}", 'telebirr_account': ''}
                    )
                self.message_user(request, f"Assigned {role_name} role to {user.email}")
            except RoleDoesNotExist:
                self.message_user(request, f"Role {role_name} does not exist for {user.email}.", level='error')

    def assign_buyer_role(self, request, queryset):
        self._assign_role(request, queryset, 'buyer')

    assign_buyer_role.short_description = "Assign Buyer role"

    def assign_dealer_role(self, request, queryset):
        self._assign_role(request, queryset, 'dealer')

    assign_dealer_role.short_description = "Assign Dealer role"

    def assign_broker_role(self, request, queryset):
        self._assign_role(request, queryset, 'broker')

    assign_broker_role.short_description = "Assign Broker role"

    def assign_admin_role(self, request, queryset):
        self._assign_role(request, queryset, 'admin')

    assign_admin_role.short_description = "Assign Admin role"

    def assign_superadmin_role(self, request, queryset):
        self._assign_role(request, queryset, 'superadmin')

    assign_superadmin_role.short_description = "Assign SuperAdmin role"


# Profile Admin
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user_email", "first_name", "last_name", "contact", "address", "image_preview", "created_at")
    search_fields = ("user__email", "first_name", "last_name", "contact", "address")
    list_filter = ("created_at",)
    readonly_fields = ("created_at", "updated_at", "image_preview")
    inlines = [BuyerProfileInline, DealerProfileInline, BrokerProfileInline]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User Email"

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" />', obj.image.url)
        return "No image"

    image_preview.short_description = "Image Preview"


# BuyerProfile Admin
@admin.register(BuyerProfile)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ("id", "profile_user_email", "loyalty_points")
    search_fields = ("profile__user__email",)
    list_filter = ("loyalty_points",)
    readonly_fields = ("loyalty_points",)

    def profile_user_email(self, obj):
        return obj.profile.user.email

    profile_user_email.short_description = "User Email"


# DealerProfile Admin
@admin.register(DealerProfile)
class DealerAdmin(admin.ModelAdmin):
    list_display = ("id", "profile_user_email", "company_name", "license_number", "tax_id", "telebirr_account",
                    "is_verified")
    search_fields = ("profile__user__email", "company_name", "license_number", "tax_id", "telebirr_account")
    list_filter = ("is_verified",)
    readonly_fields = ("is_verified",)

    def profile_user_email(self, obj):
        return obj.profile.user.email

    profile_user_email.short_description = "User Email"


# BrokerProfile Admin
@admin.register(BrokerProfile)
class BrokerAdmin(admin.ModelAdmin):
    list_display = ("id", "profile_user_email", "national_id", "telebirr_account", "is_verified")
    search_fields = ("profile__user__email", "national_id", "telebirr_account")
    list_filter = ("is_verified",)
    readonly_fields = ("is_verified",)

    def profile_user_email(self, obj):
        return obj.profile.user.email

    profile_user_email.short_description = "User Email"


# LoyaltyProgram Admin
@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer_profile_user_email", "points", "reward", "created_at")
    search_fields = ("buyer__profile__user__email", "reward")
    list_filter = ("points", "created_at")
    readonly_fields = ("points", "reward", "created_at")

    def buyer_profile_user_email(self, obj):
        return obj.buyer.profile.user.email

    buyer_profile_user_email.short_description = "User Email"


# BrokerRating Admin
@admin.register(BrokerRating)
class BrokerRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "broker_profile_user_email", "user_email", "rating", "comment", "created_at")
    search_fields = ("broker__profile__user__email", "user__email", "comment")
    list_filter = ("rating", "created_at")
    readonly_fields = ("created_at", "updated_at")

    def broker_profile_user_email(self, obj):
        return obj.broker.profile.user.email

    broker_profile_user_email.short_description = "Broker Email"

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User Email"


# DealerRating Admin
@admin.register(DealerRating)
class DealerRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "dealer_profile_user_email", "user_email", "rating", "comment", "created_at")
    search_fields = ("dealer__profile__user__email", "user__email", "comment")
    list_filter = ("rating", "created_at")
    readonly_fields = ("created_at", "updated_at")

    def dealer_profile_user_email(self, obj):
        return obj.dealer.profile.user.email

    dealer_profile_user_email.short_description = "Dealer Email"

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User Email"


class CarImageInline(admin.TabularInline):
    model = CarImage
    extra = 1
    fields = ('image', 'is_featured', 'caption', 'uploaded_at', 'image_preview')
    readonly_fields = ('uploaded_at', 'image_preview')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" />', str(obj.image))
        return "No image"

    image_preview.short_description = "Image Preview"


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = (
        'make', 'model', 'year', 'price', 'mileage', 'fuel_type', 'body_type',
        'status', 'sale_type', 'verification_status', 'priority', 'created_at'
    )
    search_fields = ('make', 'model', 'year', 'fuel_type', 'body_type', 'status')
    list_filter = (
        'make_ref', 'year', 'fuel_type', 'body_type', 'status', 'sale_type',
        'verification_status', 'priority'
    )
    autocomplete_fields = ['make_ref', 'model_ref']
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CarImageInline]
    fields = (
        'make', 'model', 'make_ref', 'model_ref', 'year', 'price', 'mileage',
        'fuel_type', 'body_type', 'status', 'sale_type', 'auction_end', 'dealer',
        'broker', 'posted_by', 'verification_status', 'priority',
        'created_at', 'updated_at'
    )

    def get_changeform_initial_data(self, request):
        """
        Pre-fill 'body_type' with the most frequent value in the database.
        """
        initial = super().get_changeform_initial_data(request)
        most_common_body = (
            Car.objects.values('body_type')
            .annotate(count=Count('body_type'))
            .order_by('-count')
            .first()
        )
        if most_common_body:
            initial['body_type'] = most_common_body['body_type']
        return initial

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not has_role(request.user, ['admin', 'super_admin']) and not request.user.is_superuser:
            return qs.filter(verification_status='verified')
        return qs

    def has_add_permission(self, request):
        return has_role(request.user, ['dealer', 'broker', 'admin', 'super_admin']) or request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return has_role(request.user, ['dealer', 'broker', 'admin', 'super_admin']) or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return has_role(request.user, ['admin', 'super_admin']) or request.user.is_superuser


@admin.register(CarImage)
class CarImageAdmin(admin.ModelAdmin):
    list_display = ('car', 'is_featured', 'caption', 'uploaded_at', 'image_preview')
    search_fields = ('car__make', 'car__model', 'caption')
    list_filter = ('is_featured', 'uploaded_at')
    readonly_fields = ('uploaded_at', 'image_preview')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" />', str(obj.image))
        return "No image"

    image_preview.short_description = "Image Preview"
