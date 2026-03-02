from django.db import transaction

from online_car_market.inventory.models import CarImage
from online_car_market.brokers.models import BrokerProfile
from rest_framework.exceptions import PermissionDenied, ValidationError

class CarService:

    @staticmethod
    def validate_broker_can_post(user):
        if user.has_role('broker'):
            try:
                broker_profile = BrokerProfile.objects.get(profile__user=user)
                if not broker_profile.can_post:
                    raise PermissionDenied("Broker must complete payment to post cars.")
            except BrokerProfile.DoesNotExist:
                raise ValidationError("Broker profile not found.")

    @staticmethod
    @transaction.atomic
    def create_car_with_images(serializer, request):
        """
        Creates a Car instance and its associated images.
        Works with both:
        1. Indexed form-data: uploaded_images[0].image_file
        2. Simple list: uploaded_images
        """
        # Save the car first
        car = serializer.save()

        uploaded_images = {}

        # Handle indexed keys (uploaded_images[0].image_file)
        for key, file in request.FILES.items():
            if key.startswith("uploaded_images"):
                if "]." in key:
                    # Extract index and field name
                    index = key.split('[')[1].split(']')[0]
                    field_name = key.split('].')[1]

                    if index not in uploaded_images:
                        uploaded_images[index] = {}
                    uploaded_images[index][field_name] = file
                else:
                    # Simple list case
                    uploaded_images.setdefault(key, {})["image_file"] = file

        if not uploaded_images:
            raise ValidationError("No images uploaded.")

        first_image = None
        for i, img_data in enumerate(uploaded_images.values()):
            image = CarImage.objects.create(
                car=car,
                image=img_data.get("image_file"),
                caption=img_data.get("caption", ""),
                is_featured=img_data.get("is_featured", i == 0)  # first image default featured
            )
            if i == 0:
                first_image = image

        # Ensure at least one featured image
        if not CarImage.objects.filter(car=car, is_featured=True).exists() and first_image:
            first_image.is_featured = True
            first_image.save()

        return car
