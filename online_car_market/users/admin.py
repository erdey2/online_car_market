from django.contrib import admin
from rolepermissions.admin import RolePermissionsUserAdmin
from django.contrib.auth import get_user_model

from online_car_market.buyers.models import Buyer
from online_car_market.dealers.models import Dealer
from online_car_market.brokers.models import Broker

User = get_user_model()

# --------------------------
# Unregister User first
# --------------------------
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

# --------------------------
# Custom User Admin
# --------------------------
@admin.register(User)
class CustomUserAdmin(RolePermissionsUserAdmin):
    # Replace 'username' with 'email' because your User model doesn't have 'username'
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")

# --------------------------
# Buyer Admin
# --------------------------
@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ("id", "user")  # replace with actual fields if you have more
    search_fields = ("user__email",)

# --------------------------
# Dealer Admin
# --------------------------
@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "company_name")  # replace with actual fields
    search_fields = ("user__email", "company_name")

# --------------------------
# Broker Admin
# --------------------------
@admin.register(Broker)
class BrokerAdmin(admin.ModelAdmin):
    list_display = ("id", "user")  # replace with actual fields
    search_fields = ("user__email",)
