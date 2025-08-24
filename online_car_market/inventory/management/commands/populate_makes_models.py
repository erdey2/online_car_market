from django.core.management.base import BaseCommand
from online_car_market.inventory.models import CarMake, CarModel

class Command(BaseCommand):
    help = 'Populate common car makes and models'

    def handle(self, *args, **kwargs):
        makes = [
            {'name': 'Toyota', 'models': ['Aurion', 'Avalon', 'Avensis', 'Axio', 'Land Cruiser', 'Yaris', 'Estima',  'Corolla', 'Camry', 'RAV4']},
            {'name': 'Honda', 'models': ['Civic', 'Accord', 'CR-V', 'CR-X', 'HR-V']},
            {'name': 'Ford', 'models': ['Bronco', 'Corsair', 'Cortina', 'Escort', 'F-150', 'Mustang', 'Explorer']},
            {'name': 'Jaguar', 'models': [' XJR', 'XJ6', 'F-Type', ' S-Type', 'X-Type', ' E-Type']},
            {'name': 'Suzuki', 'models': ['Alto', 'Baleno', 'Grand Vitara', ' Ignis', ' Jimmy', ' Liana', 'Sierra', 'Swift', ' Carry']},
        ]
        for make_data in makes:
            make, _ = CarMake.objects.get_or_create(name=make_data['name'])
            for model_name in make_data['models']:
                CarModel.objects.get_or_create(make=make, name=model_name)
        self.stdout.write(self.style.SUCCESS('Successfully populated makes and models'))
