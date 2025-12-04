from rest_framework import serializers

class CarViewAnalyticsSerializer(serializers.Serializer):
    car_id = serializers.IntegerField()
    car_make = serializers.CharField()
    car_model = serializers.CharField()
    email = serializers.CharField(allow_null=True, required=False)
    total_views = serializers.IntegerField()
