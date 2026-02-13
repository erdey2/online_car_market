from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from django.db.models import Avg, Count
from ..models import CarRating
from .serializers import CarRatingSerializer, CarRatingReadSerializer
from online_car_market.inventory.models import Car
from online_car_market.inventory.api.serializers import CarListSerializer


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
    ),
    ratings_stats=extend_schema(
        summary="List cars with aggregated ratings",
        description="Returns each car with average rating and rating count",
        responses=OpenApiResponse(
            response=CarListSerializer(many=True),
            description="Car list with avg_rating and rating_count"
        )
    )
)
class CarRatingViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CarRating.objects.select_related('car', 'user')

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return CarRatingReadSerializer
        return CarRatingSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.user != self.request.user:
            raise ValidationError("You can only edit your own rating.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise ValidationError("You can only delete your own rating.")
        instance.delete()

    @action(detail=False, methods=['get'], url_path='ratings-stats', url_name='ratings_stats')
    def ratings_stats(self, request):
        """
        Returns a list of all cars with aggregated ratings:
        - avg_rating
        - rating_count
        """
        cars = Car.objects.all().annotate(
            avg_rating=Avg('ratings__rating'),
            rating_count=Count('ratings')
        )
        serializer = CarListSerializer(cars, many=True)
        return Response(serializer.data)
