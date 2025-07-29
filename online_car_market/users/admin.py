from django.contrib import admin
from .models import User
from online_car_market.buyers.models import Buyer, Dealer
from online_car_market.brokers.models import Broker

admin.site.register(User)
admin.site.register(Buyer)
admin.site.register(Broker)
admin.site.register(Dealer)

