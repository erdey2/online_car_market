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
    def create_car_with_images(serializer, request):
        car = serializer.save()

        uploaded_images = []
        for key, file in request.FILES.items():
            if key.startswith("uploaded_images"):
                index = key.split('[')[1].split(']')[0]
                caption = request.data.get(f"uploaded_images[{index}].caption")
                is_featured = request.data.get(
                    f"uploaded_images[{index}].is_featured", "false"
                ).lower() == "true"

                uploaded_images.append({
                    "image_file": file,
                    "caption": caption,
                    "is_featured": is_featured
                })

        first_image = None
        for i, img in enumerate(uploaded_images):
            image = CarImage.objects.create(
                car=car,
                image=img['image_file'],
                caption=img['caption'],
                is_featured=img['is_featured']
            )
            if i == 0:
                first_image = image

        if not CarImage.objects.filter(car=car, is_featured=True).exists() and first_image:
            first_image.is_featured = True
            first_image.save()

        return car
