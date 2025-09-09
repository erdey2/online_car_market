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
    list_display = ['make', 'model', 'year', 'price', 'featured_image_preview']
    inlines = [CarImageInline]

    def featured_image_preview(self, obj):
        featured = obj.images.filter(is_featured=True).first()
        if featured and featured.image:
            return format_html('<img src="{}" style="height: 80px;" />', featured.image.url)
        return "No featured image"
    featured_image_preview.short_description = "Featured Image"

# admin.site.register(Car, CarAdmin)
