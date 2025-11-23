from rest_framework import serializers
from ..models import Notification, Device


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = ('id','actor','verb','description','data','is_read','created_at')

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ('id','fcm_token','platform')
