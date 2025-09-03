from django.contrib import admin
from django.contrib.auth import get_user_model
from rolepermissions.admin import RolePermissionsUserAdmin
from rolepermissions.roles import get_user_roles
from online_car_market.users.models import Profile
from online_car_market.buyers.models import BuyerProfile, LoyaltyProgram
from online_car_market.dealers.models import DealerProfile, DealerRating
from online_car_market.brokers.models import BrokerProfile, BrokerRating

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
    fields = ['first_name', 'last_name', 'contact', 'address', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

# Inline for BuyerProfile under Profile
class BuyerProfileInline(admin.StackedInline):
    model = BuyerProfile
    can_delete = False
    verbose_name_plural = 'Buyer Profile'
    fields = ['loyalty_points']

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

    def get_roles(self, obj):
        return ", ".join([role.get_name() for role in get_user_roles(obj)])
    get_roles.short_description = "Roles"

# Profile Admin
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user_email", "first_name", "last_name", "contact", "address", "created_at")
    search_fields = ("user__email", "first_name", "last_name", "contact", "address")
    list_filter = ("created_at",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [BuyerProfileInline, DealerProfileInline, BrokerProfileInline]

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User Email"

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
    list_display = ("id", "profile_user_email", "company_name", "license_number", "tax_id", "telebirr_account", "is_verified")
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
