from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext

from online_car_market.inventory.models import CarMake, CarModel, Car
from online_car_market.dealers.models import DealerProfile
from online_car_market.users.models import Profile


class PopularCarsQueryTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(email='test2@example.com', password='pass')

        make = CarMake.objects.create(name='MakeB')
        model = CarModel.objects.create(make=make, name='ModelB')

        # create a dealer to satisfy model constraint (either dealer or broker required)
        dealer_user = get_user_model().objects.create_user(email='dealer@example.com', password='pass')
        dealer_profile = Profile.objects.create(user=dealer_user)
        dealer = DealerProfile.objects.create(profile=dealer_profile, company_name='DealerCo', license_number='LIC123')

        # create several verified cars
        for i in range(5):
            Car.objects.create(
                make_ref=make,
                model_ref=model,
                year=2020 + i,
                price=1000 + i,
                mileage=100 + i,
                fuel_type='petrol',
                posted_by=self.user,
                verification_status='verified',
                views_count=i,
                dealer=dealer,
            )

    def test_popular_cars_list_query_count(self):
        url = reverse('popular-car-list')

        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(url)

        # Response should be OK and paginated
        self.assertEqual(resp.status_code, 200)
        # Ensure the view does not run excessive queries (count + data + small overhead)
        self.assertLessEqual(len(ctx), 6, msg=f"Too many queries: {len(ctx)}")
        # Results should be present
        data = resp.json()
        self.assertIn('results', data)
        self.assertGreater(len(data['results']), 0)



