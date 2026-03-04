from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError
from online_car_market.inventory.models import CarImage
from online_car_market.brokers.models import BrokerProfile


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

        # Save car first
        car = serializer.save()

        uploaded_images = {}

        # Collect text fields (caption, is_featured)
        for key in request.data:
            if key.startswith("uploaded_images") and "]." in key:
                index = key.split("[")[1].split("]")[0]
                field_name = key.split("].")[1]

                uploaded_images.setdefault(index, {})
                uploaded_images[index][field_name] = request.data.get(key)

        # Attach files
        for key, file in request.FILES.items():
            if key.startswith("uploaded_images") and "]." in key:
                index = key.split("[")[1].split("]")[0]
                field_name = key.split("].")[1]

                uploaded_images.setdefault(index, {})
                uploaded_images[index][field_name] = file

        if not uploaded_images:
            raise ValidationError("At least one image is required.")

        # Create images properly
        created_images = []
        featured_exists = False

        for index in sorted(uploaded_images.keys(), key=int):
            img_data = uploaded_images[index]

            is_featured = str(
                img_data.get("is_featured", "false")
            ).lower() == "true"

            # Ensure only ONE featured
            if is_featured and featured_exists:
                is_featured = False

            image = CarImage.objects.create(
                car=car,
                image=img_data.get("image_file"),
                caption=img_data.get("caption", ""),
                is_featured=is_featured,
            )

            if is_featured:
                featured_exists = True

            created_images.append(image)

        # If none marked featured → make first one featured
        if not featured_exists and created_images:
            first_image = created_images[0]
            first_image.is_featured = True
            first_image.save(update_fields=["is_featured"])

        return car
