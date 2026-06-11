from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from django.db.models import Avg, Count

from ..models import CarRating
from .serializers import CarRatingSerializer, CarRatingReadSerializer, CarRatingsStatsSerializer
from online_car_market.inventory.models import Car
from online_car_market.inventory.api.serializers import CarListSerializer
from online_car_market.notifications.services import notify_user
from online_car_market.users.permissions.drf_permissions import IsBuyer


@extend_schema_view(
    list=extend_schema(
        summary="List all car ratings",
        description="Retrieve a list of all car ratings with car and user info",
        responses=CarRatingReadSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Retrieve a car rating",
        description="Retrieve details of a single car rating by ID",
        responses=CarRatingReadSerializer,
    ),
    create=extend_schema(
        summary="Create a new car rating",
        description=(
            "Authenticated buyers can create a rating for a car. "
            "Only one rating per user per car is allowed."
        ),
        request=CarRatingSerializer,
        responses={
            201: CarRatingSerializer,
            400: OpenApiResponse(
                description="Validation error: already rated or invalid input"
            ),
            403: OpenApiResponse(
                description="Only buyers can create ratings"
            ),
        },
    ),
    update=extend_schema(
        summary="Update a car rating",
        description="Buyers can update their own car rating.",
        request=CarRatingSerializer,
        responses={
            200: CarRatingSerializer,
            403: OpenApiResponse(
                description="Forbidden: cannot edit others' ratings"
            ),
        },
    ),
    partial_update=extend_schema(
        summary="Partially update a car rating",
        description="Buyers can partially update their own car rating.",
        request=CarRatingSerializer,
        responses={
            200: CarRatingSerializer,
            403: OpenApiResponse(
                description="Forbidden: cannot edit others' ratings"
            ),
        },
    ),
    destroy=extend_schema(
        summary="Delete a car rating",
        description="Buyers can delete their own car rating.",
        responses={
            204: OpenApiResponse(
                description="Rating deleted successfully"
            ),
            403: OpenApiResponse(
                description="Forbidden: cannot delete others' ratings"
            ),
        },
    ),
    ratings_stats=extend_schema(
        summary="List cars with aggregated ratings",
        description="Returns each car with average rating and rating count",
        responses=OpenApiResponse(
            response=CarListSerializer(many=True),
            description="Car list with avg_rating and rating_count",
        ),
    ),
)
class CarRatingViewSet(ModelViewSet):

    def get_permissions(self):
        if self.action in ["list", "retrieve", "ratings_stats"]:
            permissions = [AllowAny]

        elif self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
        ]:
            permissions = [IsBuyer]

        else:
            permissions = [IsAuthenticated]

        return [permission() for permission in permissions]

    def get_queryset(self):
        return CarRating.objects.select_related("car", "user")

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return CarRatingReadSerializer
        return CarRatingSerializer

    def get_object(self):
        obj = super().get_object()

        if self.action in ["update", "partial_update", "destroy"]:
            if obj.user != self.request.user:
                raise PermissionDenied(
                    "You can only manage your own ratings."
                )

        return obj

    def perform_create(self, serializer):
        rating = serializer.save(user=self.request.user)

        car = rating.car
        owner = car.posted_by

        if owner != self.request.user:
            notify_user(
                user=owner,
                message=(
                    f"Your car {car.make} {car.model} "
                    f"received a {rating.rating} ⭐ rating"
                ),
                data={
                    "type": "car_rating",
                    "car_id": car.id,
                    "rating": rating.rating,
                    "user_id": self.request.user.id,
                },
            )

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

    @action(
        detail=False,
        methods=["get"],
        url_path="ratings-stats",
        url_name="ratings_stats",
    )
    def ratings_stats(self, request):
        cars = (
            Car.objects.only("id", "make", "model")
            .annotate(
                avg_rating=Avg("ratings__rating"),
                rating_count=Count("ratings"),
            )
        )

        serializer = CarRatingsStatsSerializer(cars, many=True)
        return Response(serializer.data)
