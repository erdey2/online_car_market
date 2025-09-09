# inventory/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Car, CarImage, CarMake, CarModel

# --- Car Make & Model Admin ---
@admin.register(CarMake)
class CarMakeAdmin(admin.ModelAdmin):
    search_fields = ["name"]

@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    search_fields = ["name"]

# --- CarImage Inline ---
class CarImageInline(admin.TabularInline):
    model = CarImage
    extra = 1
    fields = ['image_preview', 'image', 'is_featured', 'caption', 'uploaded_at']
    readonly_fields = ['image_preview', 'uploaded_at']

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="100" style="object-fit: cover;"/>',
                obj.image.url
            )
        return "No image"

    image_preview.short_description = "Image Preview"

# --- Car Admin ---
@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ['make', 'model', 'year', 'price', 'mileage', 'fuel_type', 'body_type',  'featured_image_preview']
    search_fields = ['make', 'model', 'year', 'fuel_type', 'body_type']
    list_filter = ['make_ref', 'year', 'fuel_type', 'body_type', 'status', 'sale_type', 'verification_status', 'priority']
    autocomplete_fields = ['make_ref', 'model_ref']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CarImageInline]

    fields = (
        'make', 'model', 'make_ref', 'model_ref', 'year', 'price', 'mileage',
        'fuel_type', 'body_type', 'exterior_color', 'interior_color', 'engine',
        'bluetooth', 'drivetrain', 'status', 'sale_type', 'auction_end',
        'dealer', 'broker', 'posted_by', 'verification_status', 'priority',
        'created_at', 'updated_at'
    )

    def featured_image_preview(self, obj):
        """
        Display featured image. If none is marked, pick the first uploaded image.
        """
        featured = obj.images.filter(is_featured=True).first()
        if not featured:
            featured = obj.images.first()  # Pick first uploaded image if no featured

        if featured and featured.image:
            return format_html(
                '<img src="{}" width="80" height="80" style="object-fit: cover;" />',
                featured.image.url
            )
        return "No image"

    featured_image_preview.short_description = "Featured Image"

@admin.register(CarImage)
class CarImageAdmin(admin.ModelAdmin):
    list_display = ('car__make', 'car__model', 'car__price',  'is_featured', 'caption', 'uploaded_at', 'image_preview')
    search_fields = ('car__make', 'car__model', 'caption')
    list_filter = ('is_featured', 'uploaded_at')
    readonly_fields = ('uploaded_at', 'image_preview')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return "No image"

    image_preview.short_description = "Image Preview"

