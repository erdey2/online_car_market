import re

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError
from online_car_market.inventory.models import CarImage
from online_car_market.notifications.services import notify_user
from .favorite_car_service import FavoriteCarService

class CarService:

    @staticmethod
    def _collect_uploaded_images(request):
        uploaded_images = {}
        bracket_pattern = re.compile(
            r"^uploaded_images\[(\d+)\](?:\.|\[)([a-zA-Z_]+)\]?$"
        )

        def _ingest(key, value):
            match = bracket_pattern.match(key)
            if match:
                index, field_name = match.group(1), match.group(2)
                uploaded_images.setdefault(index, {})
                uploaded_images[index][field_name] = value

        for key in request.data:
            if key.startswith("uploaded_images"):
                _ingest(key, request.data.get(key))

        for key, file in request.FILES.items():
            if key.startswith("uploaded_images"):
                _ingest(key, file)

        return uploaded_images

    @staticmethod
    def _attach_images_to_car(car, uploaded_images, *, require_at_least_one=False):
        if not uploaded_images:
            if require_at_least_one:
                raise ValidationError("At least one image is required.")
            return

        created_images = []
        featured_exists = CarImage.objects.filter(car=car, is_featured=True).exists()

        for index in sorted(uploaded_images.keys(), key=int):
            img_data = uploaded_images[index]
            image_file = img_data.get("image_file")

            if not image_file:
                raise ValidationError("Each image must include an image_file.")

            is_featured = str(img_data.get("is_featured", "false")).lower() == "true"

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

        if not featured_exists and created_images:
            first_image = created_images[0]
            first_image.is_featured = True
            first_image.save(update_fields=["is_featured"])

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

        car = serializer.save()
        uploaded_images = CarService._collect_uploaded_images(request)
        CarService._attach_images_to_car(car, uploaded_images, require_at_least_one=True)
        return car

    @staticmethod
    @transaction.atomic
    def update_car_with_images(serializer, request):
        old_price = serializer.instance.price
        car = serializer.save()
        uploaded_images = CarService._collect_uploaded_images(request)
        CarService._attach_images_to_car(car, uploaded_images, require_at_least_one=False)

        if car.price < old_price:
            CarService.notify_price_drop(car, old_price, car.price)

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
