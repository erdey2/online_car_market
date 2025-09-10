from rest_framework import serializers
from online_car_market.users.models import Profile

class ProfileLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'first_name', 'last_name', 'contact', 'address', 'image']
        read_only_fields = ['id', 'image']
