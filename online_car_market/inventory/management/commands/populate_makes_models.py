from django.core.management.base import BaseCommand
from online_car_market.inventory.models import CarMake, CarModel

CAR_DATA = [
    {"make": "Toyota", "models": ["Corolla", "Camry", "RAV4", "Hilux", "Land Cruiser", "Yaris"]},
    {"make": "Honda", "models": ["Civic", "Accord", "CR-V", "Fit", "HR-V", "Pilot"]},
    {"make": "Ford", "models": ["F-150", "Focus", "Explorer", "Escape", "Mustang", "Ranger"]},
    {"make": "Chevrolet", "models": ["Silverado", "Malibu", "Equinox", "Tahoe", "Camaro", "Trailblazer"]},
    {"make": "Nissan", "models": ["Altima", "Sentra", "Rogue", "Pathfinder", "Frontier", "Titan"]},
    {"make": "Hyundai", "models": ["Elantra", "Sonata", "Tucson", "Santa Fe", "Kona", "Accent"]},
    {"make": "Kia", "models": ["Sorento", "Sportage", "Optima", "Rio", "Telluride", "Soul"]},
    {"make": "Volkswagen", "models": ["Golf", "Passat", "Tiguan", "Jetta", "Atlas", "Beetle"]},
    {"make": "BMW", "models": ["3 Series", "5 Series", "7 Series", "X3", "X5", "M3"]},
    {"make": "Mercedes-Benz", "models": ["C-Class", "E-Class", "S-Class", "GLC", "GLE", "A-Class"]},
    {"make": "Audi", "models": ["A3", "A4", "A6", "Q3", "Q5", "Q7"]},
    {"make": "Lexus", "models": ["RX", "ES", "NX", "IS", "GX", "LX"]},
    {"make": "Mazda", "models": ["Mazda3", "Mazda6", "CX-3", "CX-5", "CX-9", "MX-5"]},
    {"make": "Subaru", "models": ["Impreza", "Forester", "Outback", "Crosstrek", "Legacy", "WRX"]},
    {"make": "Jeep", "models": ["Wrangler", "Grand Cherokee", "Cherokee", "Compass", "Renegade", "Gladiator"]},
    {"make": "Dodge", "models": ["Charger", "Challenger", "Durango", "Journey", "Ram 1500"]},
    {"make": "Ram", "models": ["1500", "2500", "3500"]},
    {"make": "GMC", "models": ["Sierra", "Yukon", "Acadia", "Terrain", "Canyon"]},
    {"make": "Tesla", "models": ["Model 3", "Model S", "Model X", "Model Y", "Cybertruck"]},
    {"make": "Volvo", "models": ["XC40", "XC60", "XC90", "S60", "S90", "V60"]},
    {"make": "Jaguar", "models": ["XE", "XF", "XJ", "F-Pace", "E-Pace", "I-Pace"]},
    {"make": "Land Rover", "models": ["Range Rover", "Range Rover Sport", "Discovery", "Defender", "Evoque"]},
    {"make": "Porsche", "models": ["911", "Cayenne", "Macan", "Panamera", "Taycan"]},
    {"make": "Ferrari", "models": ["488", "Roma", "Portofino", "SF90", "F8 Tributo"]},
    {"make": "Lamborghini", "models": ["Huracan", "Aventador", "Urus"]},
    {"make": "Mitsubishi", "models": ["Outlander", "Eclipse Cross", "Mirage", "Pajero"]},
    {"make": "Peugeot", "models": ["208", "308", "508", "3008", "5008"]},
    {"make": "Renault", "models": ["Clio", "Megane", "Captur", "Koleos"]},
    {"make": "Suzuki", "models": ["Swift", "Vitara", "Jimny", "Baleno"]},
    {"make": "Fiat", "models": ["500", "Panda", "Tipo", "Punto"]},
]

class Command(BaseCommand):
    help = 'Load car makes and models into the database'

    def handle(self, *args, **options):
        for entry in CAR_DATA:
            make_name = entry["make"]
            make, _ = CarMake.objects.get_or_create(name=make_name)
            for model_name in entry["models"]:
                CarModel.objects.get_or_create(make=make, name=model_name)
            self.stdout.write(self.style.SUCCESS(f"Loaded {make_name} and its models"))
