from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.db.models import Avg

from ..models import CarRating
from .serializers import CarRatingSerializer, CarRatingReadSerializer


class CarRatingViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        - Users see ratings for all cars (read)
        - Users can only update/delete their own ratings
        """
        return CarRating.objects.select_related('car', 'user')

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return CarRatingReadSerializer
        return CarRatingSerializer

    def perform_create(self, serializer):
        try:
            serializer.save()
        except Exception:
            raise ValidationError("You have already rated this car.")

    def perform_update(self, serializer):
        if serializer.instance.user != self.request.user:
            raise ValidationError("You can only edit your own rating.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise ValidationError("You can only delete your own rating.")
        instance.delete()
