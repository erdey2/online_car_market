import json
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
    def _parse_image_id(raw_id):
        if raw_id in (None, ""):
            return None
        try:
            return int(raw_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Invalid image id.") from exc

    @staticmethod
    def _parse_bool(value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")

    @staticmethod
    def _get_car_image(car, image_id):
        try:
            return CarImage.objects.get(pk=image_id, car=car)
        except CarImage.DoesNotExist as exc:
            raise ValidationError(
                f"Image {image_id} does not belong to this car."
            ) from exc

    @staticmethod
    def _apply_image_fields(image, img_data, *, image_file=None):
        if image_file is not None:
            image.image = image_file
        if "caption" in img_data:
            image.caption = img_data.get("caption") or ""
        if "is_featured" in img_data:
            image.is_featured = CarService._parse_bool(img_data.get("is_featured"))
        image.save()

    @staticmethod
    def _upsert_images_for_car(car, uploaded_images, *, require_at_least_one=False):
        """
        Create or update car images from multipart uploaded_images[n] fields.

        - New image: uploaded_images[n].image_file (no id)
        - Edit existing: uploaded_images[n].id + optional image_file, caption, is_featured
        """
        if not uploaded_images:
            if require_at_least_one and not car.images.exists():
                raise ValidationError("At least one image is required.")
            return

        touched = []

        for index in sorted(uploaded_images.keys(), key=int):
            img_data = uploaded_images[index]
            image_id = CarService._parse_image_id(img_data.get("id"))
            image_file = img_data.get("image_file")

            if image_id is not None:
                image = CarService._get_car_image(car, image_id)
                if not image_file and "caption" not in img_data and "is_featured" not in img_data:
                    raise ValidationError(
                        "When updating an image, provide image_file, caption, and/or is_featured."
                    )
                CarService._apply_image_fields(image, img_data, image_file=image_file)
                touched.append(image)
                continue

            if require_at_least_one or image_file:
                if not image_file:
                    raise ValidationError(
                        "Each new image must include an image_file."
                    )

                is_featured = CarService._parse_bool(img_data.get("is_featured"))
                if is_featured and car.images.filter(is_featured=True).exists():
                    is_featured = False

                image = CarImage.objects.create(
                    car=car,
                    image=image_file,
                    caption=img_data.get("caption") or "",
                    is_featured=is_featured,
                )
                touched.append(image)

        if require_at_least_one and not car.images.exists():
            raise ValidationError("At least one image is required.")

        if touched and not car.images.filter(is_featured=True).exists():
            first_image = car.images.order_by("id").first()
            if first_image:
                first_image.is_featured = True
                first_image.save(update_fields=["is_featured"])

    @staticmethod
    def sync_images_json(car, images_payload):
        """Update existing images from JSON (id required per item; no new binary uploads)."""
        if images_payload in (None, ""):
            return

        if isinstance(images_payload, str):
            try:
                images_payload = json.loads(images_payload)
            except json.JSONDecodeError as exc:
                raise ValidationError("Invalid images JSON payload.") from exc

        if not isinstance(images_payload, list):
            raise ValidationError("images must be a list.")

        for item in images_payload:
            if not isinstance(item, dict):
                raise ValidationError("Each image entry must be an object.")

            image_id = CarService._parse_image_id(item.get("id"))
            if image_id is None:
                raise ValidationError(
                    "JSON image updates must include id. "
                    "Use uploaded_images with image_file to add new photos."
                )

            image = CarService._get_car_image(car, image_id)
            CarService._apply_image_fields(image, item)

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
        CarService._upsert_images_for_car(car, uploaded_images, require_at_least_one=True)
        return car

    @staticmethod
    @transaction.atomic
    def update_car_with_images(serializer, request):
        old_price = serializer.instance.price
        car = serializer.save()
        uploaded_images = CarService._collect_uploaded_images(request)

        import logging
        logger = logging.getLogger(__name__)
        logger.debug("uploaded_images parsed: %r", uploaded_images)
        CarService._upsert_images_for_car(car, uploaded_images, require_at_least_one=False)

        images_payload = request.data.get("images")
        if images_payload is not None:
            CarService.sync_images_json(car, images_payload)

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
