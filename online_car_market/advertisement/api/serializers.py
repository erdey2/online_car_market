from rest_framework import serializers

from online_car_market.advertisement.models import Advertisement


class AdvertisementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Advertisement
        fields = '__all__'
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at', 'is_active')
