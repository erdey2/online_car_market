from django.contrib import admin
from .models import Car, CarImage
from django.utils.html import format_html
from .models import CarMake, CarModel

@admin.register(CarMake)
class CarMakeAdmin(admin.ModelAdmin):
    search_fields = ["name"]   # allows searching in autocomplete

@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    search_fields = ["name"]

class CarImageInline(admin.TabularInline):  # or StackedInline if you prefer vertical
    model = CarImage
    extra = 1
    fields = ['image_preview', 'image', 'is_featured', 'caption']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height: 80px;"/>', obj.image.url)
        return "No image"
    image_preview.short_description = "Preview"

class CarAdmin(admin.ModelAdmin):
    list_display = (
        'make', 'model', 'year', 'price', 'mileage', 'fuel_type', 'body_type',
        'exterior_color', 'interior_color', 'engine', 'bluetooth', 'drivetrain',
        'status', 'sale_type', 'verification_status', 'priority', 'created_at'
    )
    search_fields = (
        'make', 'model', 'year', 'fuel_type', 'body_type', 'exterior_color',
        'interior_color', 'engine', 'drivetrain', 'status'
    )
    list_filter = (
        'make_ref', 'year', 'fuel_type', 'body_type', 'exterior_color',
        'interior_color', 'engine', 'drivetrain', 'status', 'sale_type',
        'verification_status', 'priority'
    )
    autocomplete_fields = ['make_ref', 'model_ref']
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CarImageInline]
    fields = (
        'make', 'model', 'make_ref', 'model_ref', 'year', 'price', 'mileage',
        'fuel_type', 'body_type', 'exterior_color', 'interior_color', 'engine',
        'bluetooth', 'drivetrain', 'status', 'sale_type', 'auction_end', 'dealer',
        'broker', 'posted_by', 'verification_status', 'priority',
        'created_at', 'updated_at'
    )

    def featured_image_preview(self, obj):
        featured = obj.images.filter(is_featured=True).first()
        if featured and featured.image:
            return format_html('<img src="{}" style="height: 80px;" />', featured.image.url)
        return "No featured image"
    featured_image_preview.short_description = "Featured Image"

# admin.site.register(Car, CarAdmin)
