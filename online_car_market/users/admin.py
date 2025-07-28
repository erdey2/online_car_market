from django.contrib import admin
from .models import User, BuyerProfile, BrokerProfile, DealerProfile

admin.site.register(User)
admin.site.register(BuyerProfile)
admin.site.register(BrokerProfile)
admin.site.register(DealerProfile)

