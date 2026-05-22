"""Tests for car PATCH/PUT: permissions and image upload."""

from io import BytesIO
from unittest.mock import patch

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from online_car_market.brokers.models import BrokerProfile
from online_car_market.dealers.models import DealerProfile, DealerStaff
from online_car_market.inventory.models import Car, CarImage, CarMake, CarModel
from online_car_market.users.models import Profile

User = get_user_model()

MINIMAL_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"
)


def _create_user(email, role):
    user = User.objects.create_user(email=email, password="pass12345", role=role)
    Profile.objects.create(user=user, first_name="Test", last_name="User")
    return user


def _create_dealer(email):
    user = _create_user(email, User.Role.DEALER)
    dealer = DealerProfile.objects.create(
        profile=user.profile,
        company_name=f"Dealer {email}",
        license_number=f"LIC-{email}",
    )
    return user, dealer


def _create_broker(email):
    user = _create_user(email, User.Role.BROKER)
    broker = BrokerProfile.objects.create(
        profile=user.profile,
        national_id=f"NID-{email}",
        telebirr_account="tb-123",
    )
    return user, broker


def _create_car(*, dealer=None, broker=None, posted_by, price=10000):
    make = CarMake.objects.create(name=f"Make-{Car.objects.count()}")
    model = CarModel.objects.create(make=make, name="ModelX")
    return Car.objects.create(
        make_ref=make,
        model_ref=model,
        make=make.name,
        model=model.name,
        year=2022,
        price=price,
        mileage=1000,
        fuel_type="petrol",
        posted_by=posted_by,
        dealer=dealer,
        broker=broker,
        verification_status="verified",
    )


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
)
class CarUpdatePermissionTests(TestCase):
    def setUp(self):
        self._cache_patcher = patch.object(
            cache, "delete_pattern", return_value=None, create=True
        )
        self._cache_patcher.start()
        self.addCleanup(self._cache_patcher.stop)

        self.client = APIClient()
        self.dealer_user, self.dealer = _create_dealer("dealer1@test.com")
        self.other_dealer_user, self.other_dealer = _create_dealer("dealer2@test.com")
        self.broker_user, self.broker = _create_broker("broker1@test.com")
        self.other_broker_user, self.other_broker = _create_broker("broker2@test.com")
        self.admin_user = _create_user("admin@test.com", User.Role.SUPER_ADMIN)

        self.dealer_car = _create_car(
            dealer=self.dealer,
            posted_by=self.dealer_user,
            price=20000,
        )
        self.other_dealer_car = _create_car(
            dealer=self.other_dealer,
            posted_by=self.other_dealer_user,
            price=25000,
        )
        self.broker_car = _create_car(
            broker=self.broker,
            posted_by=self.broker_user,
            price=18000,
        )
        self.other_broker_car = _create_car(
            broker=self.other_broker,
            posted_by=self.other_broker_user,
            price=19000,
        )

    def _patch_price(self, user, car, price="21000"):
        self.client.force_authenticate(user=user)
        url = reverse("cars-detail", kwargs={"pk": car.pk})
        return self.client.patch(url, {"price": price}, format="json")

    def test_dealer_can_patch_own_car(self):
        response = self._patch_price(self.dealer_user, self.dealer_car)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("images", response.data)
        self.dealer_car.refresh_from_db()
        self.assertEqual(str(self.dealer_car.price), "21000.00")

    def test_dealer_cannot_patch_other_dealers_car(self):
        response = self._patch_price(self.dealer_user, self.other_dealer_car)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.other_dealer_car.refresh_from_db()
        self.assertEqual(str(self.other_dealer_car.price), "25000.00")

    def test_broker_can_patch_own_car(self):
        response = self._patch_price(self.broker_user, self.broker_car, "18500")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.broker_car.refresh_from_db()
        self.assertEqual(str(self.broker_car.price), "18500.00")

    def test_broker_cannot_patch_other_brokers_car(self):
        response = self._patch_price(self.broker_user, self.other_broker_car)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_super_admin_can_patch_any_car(self):
        response = self._patch_price(self.admin_user, self.other_dealer_car, "26000")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.other_dealer_car.refresh_from_db()
        self.assertEqual(str(self.other_dealer_car.price), "26000.00")

    def test_seller_staff_can_patch_dealer_inventory(self):
        seller = _create_user("seller@test.com", User.Role.BUYER)
        DealerStaff.objects.create(dealer=self.dealer, user=seller, role="seller")
        car = _create_car(dealer=self.dealer, posted_by=self.dealer_user, price=12000)

        response = self._patch_price(seller, car, "12500")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        car.refresh_from_db()
        self.assertEqual(str(car.price), "12500.00")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
)
class CarUpdateImageUploadTests(TestCase):
    def setUp(self):
        self._cache_patcher = patch.object(
            cache, "delete_pattern", return_value=None, create=True
        )
        self._cache_patcher.start()
        self.addCleanup(self._cache_patcher.stop)

        self.client = APIClient()
        self.dealer_user, self.dealer = _create_dealer("dealer-img@test.com")
        self.car = _create_car(
            dealer=self.dealer,
            posted_by=self.dealer_user,
            price=30000,
        )
        self.client.force_authenticate(user=self.dealer_user)
        self.url = reverse("cars-detail", kwargs={"pk": self.car.pk})

    @patch("cloudinary.uploader.upload")
    def test_patch_uploads_new_image_and_returns_detail_payload(self, mock_upload):
        mock_upload.return_value = {
            "public_id": "car-images/test",
            "secure_url": "https://res.cloudinary.com/demo/image/upload/test.jpg",
        }

        before_count = CarImage.objects.filter(car=self.car).count()

        response = self.client.patch(
            self.url,
            {
                "price": "29500",
                "uploaded_images[0].caption": "Rear view",
                "uploaded_images[0].is_featured": "false",
                "uploaded_images[0].image_file": SimpleUploadedFile(
                    "rear.jpg",
                    MINIMAL_JPEG,
                    content_type="image/jpeg",
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("images", response.data)
        self.assertEqual(CarImage.objects.filter(car=self.car).count(), before_count + 1)

        new_image = CarImage.objects.filter(car=self.car).order_by("-id").first()
        self.assertEqual(new_image.caption, "Rear view")

        self.car.refresh_from_db()
        self.assertEqual(str(self.car.price), "29500.00")
