from django.contrib import admin
from .models import Sale, Lead

admin.register(Sale)
admin.register(Lead)

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "car", "buyer", "price", "date", "broker", "dealer")
    search_fields = ("car", "price")

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "contact", "status", "assigned_sales", "car", "created_at")
    search_fields = ("car", "contact")

