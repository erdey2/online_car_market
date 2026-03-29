from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError
from online_car_market.inventory.models import CarImage
from online_car_market.notifications.services import notify_user
from .favorite_car_service import FavoriteCarService

class CarService:

    @staticmethod
    def validate_broker_can_post(user):

        if user.role == "broker":
            return  # allowed

        # Optional: restrict others
        elif user.role in ["super_admin", "admin", "dealer"]:
            return  # allowed

        raise PermissionDenied("You are not allowed to post cars.")

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

        created_images = []
        featured_exists = False

        # Create images
        for index in sorted(uploaded_images.keys(), key=int):
            img_data = uploaded_images[index]

            image_file = img_data.get("image_file")

            # Validate image existence
            if not image_file:
                raise ValidationError("Each image must include an image_file.")

            is_featured = str(
                img_data.get("is_featured", "false")
            ).lower() == "true"

            # Ensure only ONE featured
            if is_featured and featured_exists:
                is_featured = False

            image = CarImage.objects.create(
                car=car,
                image=image_file,
                caption=img_data.get("caption", ""),
                is_featured=is_featured,
            )

            if is_featured:
                featured_exists = True

            created_images.append(image)

        # If none marked featured make first one featured
        if not featured_exists and created_images:
            first_image = created_images[0]
            first_image.is_featured = True
            first_image.save(update_fields=["is_featured"])

        return car

    def notify_price_drop(car, old_price, new_price):
        favorites = FavoriteCarService.get_car_favorers(car)

        car_name = f"{car.make} {car.model} ({car.year})"

        for fav in favorites:
            notify_user(
                user=fav.user,
                message=(
                    f"Price dropped for {car_name} "
                    f"from {old_price} to {new_price}!"
                ),
                data={
                    "car_id": car.id,
                    "type": "price_drop",
                    "old_price": str(old_price),
                    "new_price": str(new_price),
                }
            )
