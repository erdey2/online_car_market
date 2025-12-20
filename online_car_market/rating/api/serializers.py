from rest_framework import serializers
from ..models import CarRating
from online_car_market.inventory.api.serializers import CarMiniSerializer
from online_car_market.inventory.models import Car

class CarRatingSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CarRating
        fields = [
            'id',
            'car',
            'user',
            'rating',
            'comment',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, attrs):
        """
        Ensure user can rate the car (example: only buyers).
        """
        user = self.context['request'].user
        car = attrs.get('car')

        # OPTIONAL business rule:
        # from online_car_market.sales.models import Sale
        # if not Sale.objects.filter(
        #     car=car,
        #     buyer=user,
        #     status='completed'
        # ).exists():
        #     raise serializers.ValidationError("You can only rate cars you have purchased.")

        return attrs

class CarRatingReadSerializer(serializers.ModelSerializer):
    car_detail = CarMiniSerializer(source='car', read_only=True)
    user = serializers.StringRelatedField()

    class Meta:
        model = CarRating
        fields = [
            'id',
            'car_detail',
            'user',
            'rating',
            'comment',
            'created_at'
        ]

