from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from django.db.models import Avg

from ..models import CarRating
from .serializers import CarRatingSerializer, CarRatingReadSerializer

@extend_schema_view(
    list=extend_schema(
        summary="List all car ratings",
        description="Retrieve a list of all car ratings with car and user info",
        responses=CarRatingReadSerializer(many=True)
    ),
    retrieve=extend_schema(
        summary="Retrieve a car rating",
        description="Retrieve details of a single car rating by ID",
        responses=CarRatingReadSerializer
    ),
    create=extend_schema(
        summary="Create a new car rating",
        description="Authenticated users can create a rating for a car. Only one rating per user per car is allowed.",
        request=CarRatingSerializer,
        responses={
            201: CarRatingSerializer,
            400: OpenApiResponse(description="Validation error: already rated or invalid input")
        }
    ),
    update=extend_schema(
        summary="Update a car rating",
        description="Users can update their own car rating.",
        request=CarRatingSerializer,
        responses={
            200: CarRatingSerializer,
            403: OpenApiResponse(description="Forbidden: cannot edit others' ratings")
        }
    ),
    partial_update=extend_schema(
        summary="Partially update a car rating",
        description="Users can partially update their own car rating.",
        request=CarRatingSerializer,
        responses={
            200: CarRatingSerializer,
            403: OpenApiResponse(description="Forbidden: cannot edit others' ratings")
        }
    ),
    destroy=extend_schema(
        summary="Delete a car rating",
        description="Users can delete their own car rating.",
        responses={
            204: OpenApiResponse(description="Rating deleted successfully"),
            403: OpenApiResponse(description="Forbidden: cannot delete others' ratings")
        }
    )
)
class CarRatingViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Users see ratings for all cars (read)
        Users can only update/delete their own ratings
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
