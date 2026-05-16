import logging

from django.core.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.core.cache import cache
from django.conf import settings

from rest_framework import status, mixins, serializers
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.filters import SearchFilter, OrderingFilter

from drf_spectacular.utils import (extend_schema, extend_schema_view, OpenApiParameter,
                                   OpenApiTypes, OpenApiExample, OpenApiResponse, inline_serializer)
from ..models import Car, CarMake, CarModel, FavoriteCar, CarView, Contact
from .serializers import (
                          VerifyCarSerializer, CarMakeSerializer, ContactSerializer,
                          CarModelSerializer, FavoriteCarSerializer, CarViewSerializer,
                          CarWriteSerializer, CarListSerializer, CarDetailSerializer,
                          CarVerificationListSerializer, CarVerificationAnalyticsSerializer
                          )
from online_car_market.users.permissions.drf_permissions import IsSuperAdminOrAdmin, IsSuperAdminOrAdminOrBuyer
from online_car_market.users.permissions.business_permissions import CanPostCar, CanViewInventory
from online_car_market.bids.api.serializers import BidSerializer

from ..services.car_service import CarService
from ..services.car_filter_service import CarFilterService
from ..services.car_query_service import CarQueryService
from ..services.car_verification_service import CarVerificationService
from ..services.car_bid_service import CarBidService
from ..services.popular_car_service import PopularCarService
from ..services.user_car_service import UserCarService
from ..services.favorite_car_service import FavoriteCarService
from ..services.contact_service import ContactService

logger = logging.getLogger(__name__)


# Pagination used by popular cars endpoint
class PopularCarsPagination(PageNumberPagination):
    """Pagination for popular cars list to avoid large payloads."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

@extend_schema_view(
    list=extend_schema(
        tags=["Cars - Makes"],
        description="List all car makes."
    ),
    retrieve=extend_schema(
        tags=["Cars - Makes"],
        description="Retrieve details of a specific car make."
    ),
    create=extend_schema(
        tags=["Cars - Makes"],
        description="Create a new car make (admin only)."
    ),
    update=extend_schema(
        tags=["Cars - Makes"],
        description="Update an existing car make (admin only)."
    ),
    partial_update=extend_schema(
        tags=["Cars - Makes"],
        description="Partially update a car make (admin only)."
    ),
    destroy=extend_schema(
        tags=["Cars - Makes"],
        description="Delete a car make (admin only)."
    ),
)
class CarMakeViewSet(ModelViewSet):
    queryset = CarMake.objects.all()
    serializer_class = CarMakeSerializer
    CACHE_KEY = "car_makes_list"

    def list(self, request, *args, **kwargs):
        # Try to get from cache
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            logger.debug(f"Serving car makes from cache")
            return Response(cached)

        # Fetch fresh data
        logger.debug(f"Cache miss for car makes; fetching from DB")
        resp = super().list(request, *args, **kwargs)

        # Cache for configurable duration (default: 1 minute for freshness)
        timeout = getattr(settings, "CAR_MAKES_CACHE_TIMEOUT", 60)
        cache.set(self.CACHE_KEY, resp.data, timeout=timeout)
        logger.debug(f"Cached car makes list for {timeout}s")

        # Add cache headers to client to prevent browser-level caching
        resp['Cache-Control'] = 'public, max-age=60'
        resp['Vary'] = 'Accept'

        return resp

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]   # No authentication required
        return [IsSuperAdminOrAdmin()]   # Only admins for create/update/delete

    def create(self, request, *args, **kwargs):
        """Override create to ensure cache invalidation fires."""
        response = super().create(request, *args, **kwargs)
        self._invalidate_makes_cache()
        return response

    def perform_create(self, serializer):
        instance = serializer.save()
        self._invalidate_makes_cache()
        return instance

    def perform_update(self, serializer):
        instance = serializer.save()
        self._invalidate_makes_cache()
        return instance

    def perform_destroy(self, instance):
        pk = instance.pk
        instance.delete()
        self._invalidate_makes_cache()

    def _invalidate_makes_cache(self):
        """Centralized cache invalidation to ensure it always fires."""
        try:
            cache.delete(self.CACHE_KEY)
            logger.info(f"Invalidated car makes cache")
        except Exception as e:
            logger.error(f"Failed to invalidate car makes cache: {e}")

@extend_schema_view(
    list=extend_schema(
        tags=["Cars - Models"],
        description="List all car models."
    ),
    retrieve=extend_schema(
        tags=["Cars - Models"],
        description="Retrieve details of a specific car model."
    ),
    create=extend_schema(
        tags=["Cars - Models"],
        description="Create a new car model (admin only)."
    ),
    update=extend_schema(
        tags=["Cars - Models"],
        description="Update an existing car model (admin only)."
    ),
    partial_update=extend_schema(
        tags=["Cars - Models"],
        description="Partially update a car model (admin only)."
    ),
    destroy=extend_schema(
        tags=["Cars - Models"],
        description="Delete a car model (admin only)."
    ),
)
class CarModelViewSet(ModelViewSet):
    serializer_class = CarModelSerializer

    def get_queryset(self):
        return (
            CarModel.objects
            .select_related("make")
            .order_by("make__name", "name")
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsSuperAdminOrAdmin()]

@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Inventory"],
        description="List cars with role-based visibility and optional filters.",
        parameters=[
            OpenApiParameter(name="broker_email", type=str, location="query")
        ],
        responses={200: CarListSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Dealers - Inventory"],
        description="Retrieve a specific car with role-based visibility.",
        responses={200: CarDetailSerializer, 404: OpenApiResponse(description="Not found")},
    ),
    create=extend_schema(tags=["Dealers - Inventory"], request=CarWriteSerializer, responses={201: CarDetailSerializer}),
    update=extend_schema(tags=["Dealers - Inventory"], request=CarWriteSerializer, responses={200: CarDetailSerializer}),
    partial_update=extend_schema(tags=["Dealers - Inventory"], request=CarWriteSerializer, responses={200: CarDetailSerializer}),
    destroy=extend_schema(tags=["Dealers - Inventory"], responses={204: None}),

    filter=extend_schema(
        tags=["Dealers - Inventory"],
        description="Filter cars based on query parameters such as price, make, model, year, etc.",
        parameters=[
            OpenApiParameter(name="price_min", type=float, location="query", description="Minimum price"),
            OpenApiParameter(name="price_max", type=float, location="query", description="Maximum price"),
            OpenApiParameter(name="make", type=str, location="query", description="Car make"),
            OpenApiParameter(name="model", type=str, location="query", description="Car model"),
            OpenApiParameter(name="year", type=int, location="query", description="Car year"),
        ],
        responses={200: CarListSerializer(many=True)}
    ),
    bid=extend_schema(
        tags=["Dealers - Inventory"],
        description="Place a bid on a specific car.",
        request=BidSerializer,
        responses={201: BidSerializer, 400: OpenApiResponse(description="Invalid bid")}
    )
)
class CarViewSet(ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    CACHE_TIMEOUT = 60 * 5  # 5 minutes

    def get_serializer_class(self):
        mapping = {
            "list": CarListSerializer,
            "retrieve": CarDetailSerializer,
            "create": CarWriteSerializer,
            "update": CarWriteSerializer,
            "partial_update": CarWriteSerializer,
            "verify": VerifyCarSerializer,
            "bid": BidSerializer,
        }
        return mapping.get(self.action, CarListSerializer)

    def get_queryset(self):
        if self.action == "list":
            base_qs = CarQueryService.for_list()
            return CarQueryService.get_visible_cars_for_user(self.request.user, base_qs)

        elif self.action == "retrieve":
            return CarQueryService.for_detail()

        return CarQueryService.base_queryset()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), CanPostCar()]
        return super().get_permissions()

    # ROLE-BASED CACHE KEY
    def _build_cache_key(self, request):
        user = request.user

        role = user.role if user.is_authenticated else "anon"
        dealer_id = self._get_dealer_id(user)

        query_params = request.GET.urlencode()

        return f"car_list_role_{role}_dealer_{dealer_id}_{query_params}"

    def list(self, request, *args, **kwargs):
        cache_key = self._build_cache_key(request)

        # Try cache
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        # Query DB
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # Store cache
        cache.set(cache_key, data, timeout=self.CACHE_TIMEOUT)

        return Response(data)

    def _get_dealer_id(self, user):
        if not user.is_authenticated:
            return "none"

        if hasattr(user, "profile") and hasattr(user.profile, "dealer_profile"):
            return user.profile.dealer_profile.id

        staff = getattr(user, "dealer_staff_assignments", None)
        if staff:
            staff_obj = staff.first()
            if staff_obj:
                return staff_obj.dealer.id

        return "none"

    def retrieve(self, request, *args, **kwargs):
        car_id = kwargs.get("pk")
        user = request.user

        role = user.role if user.is_authenticated else "anon"
        dealer_id = self._get_dealer_id(user)

        cache_key = f"car_detail_{car_id}_role_{role}_dealer_{dealer_id}"

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        cache.set(cache_key, data, timeout=self.CACHE_TIMEOUT)

        return Response(data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        car = CarService.create_car_with_images(serializer, request)

        # Invalidate cache (all car lists)
        cache.delete_pattern("car_list_role_*")
        cache.delete_pattern(f"car_detail_{car.id}_*")

        response_serializer = CarDetailSerializer(car, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = serializer.save()

        cache.delete_pattern("car_list_role_*")
        cache.delete_pattern(f"car_detail_{instance.id}_*")

    def perform_destroy(self, instance):
        car_id = instance.id
        instance.delete()

        cache.delete_pattern("car_list_role_*")
        cache.delete_pattern(f"car_detail_{car_id}_*")

    @action(detail=False, methods=["get"], url_path="filter")
    def filter(self, request):
        qs = CarFilterService.filter_cars(
            CarQueryService.get_visible_cars_for_user(request.user, CarQueryService.for_list()),
            request.query_params
        )
        return Response(CarListSerializer(qs, many=True, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def bid(self, request, pk=None):
        car = self.get_object()

        serializer = BidSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        bid = CarBidService.place_bid(
            car=car,
            serializer=serializer
        )

        return Response(
            BidSerializer(bid, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )

@extend_schema_view(
    list=extend_schema(
        tags=["Admin - Car Verification"],
        summary="List Car Verification Records",
        description=(
            "Retrieve car verification records.\n\n"
            "### Role-based visibility:\n"
            "- Super Admin/Admin: Can view all records\n"
            "- Dealer: Can view only their own records\n"
            "- Broker: Can view only their own records\n\n"
            "Optional filtering by verification status."
        ),
        parameters=[
            OpenApiParameter(
                name="verification_status",
                type=OpenApiTypes.STR,
                location="query",
                description="Filter by status: pending, verified, rejected",
                required=False,
            ),
        ],
        responses={200: CarVerificationListSerializer(many=True)},
    )
)
class CarVerificationViewSet(GenericViewSet):

    permission_classes = [IsAuthenticated]
    serializer_class = CarVerificationListSerializer

    def get_queryset(self):
        return Car.objects.select_related(
            "dealer__profile__user",
            "broker__profile__user",
            "posted_by"
        )

    def list(self, request):
        verification_status = request.query_params.get("verification_status")

        queryset = CarQueryService.get_verification_cars_for_user(
            user=request.user,
            verification_status=verification_status
        )

        serializer = self.get_serializer(
            queryset,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data)

    @extend_schema(
        tags=["Admin - Car Verification"],
        summary="Verify or Reject Car",
        description="Approve or reject a car listing (admin/super_admin only).",
        request=VerifyCarSerializer,
        responses={200: VerifyCarSerializer},
    )
    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsAuthenticated, IsSuperAdminOrAdmin],
    )
    def verify(self, request, pk=None):
        # uses optimized queryset automatically
        car = self.get_object()

        serializer = VerifyCarSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        car = CarVerificationService.verify_car(
            car=car,
            verification_status=serializer.validated_data["verification_status"],
            reviewed_by=request.user
        )

        return Response(
            VerifyCarSerializer(car).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Admin - Car Verification"],
        summary="Verification Analytics",
        description=(
            "Returns aggregated verification statistics.\n\n"
            "- Total cars\n"
            "- Pending\n"
            "- Verified\n"
            "- Rejected\n\n"
            "Admin/Super Admin only."
        ),
        responses={200: CarVerificationAnalyticsSerializer},
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsSuperAdminOrAdmin], url_path="analytics")
    def analytics(self, request):
        data = CarVerificationService.get_verification_analytics(request.user)

        serializer = CarVerificationAnalyticsSerializer(data)
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(
        tags=["User Cars"],
        summary="List my cars",
        description=(
            "List cars belonging to the authenticated user.\n\n"
            "Access rules:\n"
            "- Admin/Super Admin: All cars\n"
            "- Dealer: All cars under their dealership\n"
            "- Broker: Cars posted by the broker\n"
            "- Seller: Cars they posted under their assigned dealer\n"
        ),
        responses={
            200: CarListSerializer(many=True),
            403: OpenApiResponse(
                description="User does not have permission.",
                response={
                    "type": "object",
                    "properties": {"detail": {"type": "string"}}
                }
            ),
        },
    ),
    retrieve=extend_schema(
        tags=["User Cars"],
        summary="Retrieve my car",
        description=(
            "Retrieve a specific car belonging to the authenticated user.\n\n"
            "Returns 404 if the car does not belong to the user."
        ),
        responses={
            200: CarDetailSerializer,
            403: OpenApiResponse(
                description="User does not have permission.",
                response={
                    "type": "object",
                    "properties": {"detail": {"type": "string"}}
                }
            ),
            404: OpenApiResponse(
                description="Car not found or not owned by the user.",
                response={
                    "type": "object",
                    "properties": {"detail": {"type": "string"}}
                }
            ),
        },
    ),
)
class UserCarsViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, CanViewInventory]

    def get_serializer_class(self):
        return CarDetailSerializer if self.action == "retrieve" else CarListSerializer

    def get_queryset(self):
        return UserCarService.get_user_visible_cars(self.request.user)

    def retrieve(self, request, *args, **kwargs):
        car_id = kwargs.get("pk")

        try:
            car = UserCarService.get_base_queryset().get(id=car_id)
        except Car.DoesNotExist:
            raise NotFound("Car not found.")

            # Check access
        if not UserCarService.can_user_access_car(request.user, car):
            raise PermissionDenied("You do not have access to this car.")

        serializer = self.get_serializer(car)
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(
        tags=["Favorites"],
        description="List all favorite cars for the authenticated user. User must have the buyer role.",
        responses={
            200: FavoriteCarSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have the buyer role.",
                examples=[
                    OpenApiExample("Forbidden", value={"detail": "User does not have buyer role."})
                ]
            )
        }
    ),
    create=extend_schema(
        tags=["Favorites"],
        description="Add a car to the user's favorites. User must have the buyer role.",
        request=FavoriteCarSerializer,
        responses={
            201: FavoriteCarSerializer,
            400: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Invalid input, e.g., missing or invalid car_id.",
                examples=[
                    OpenApiExample("Invalid input", value={"detail": "Invalid car_id"})
                ]
            ),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have the buyer role.",
                examples=[
                    OpenApiExample("Forbidden", value={"detail": "User does not have buyer role."})
                ]
            )
        }
    ),
    retrieve=extend_schema(
        tags=["Favorites"],
        description="Retrieve a specific favorite car entry. User must be the owner and have the buyer role.",
        responses={
            200: FavoriteCarSerializer,
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have the buyer role.",
                examples=[
                    OpenApiExample("Forbidden", value={"detail": "User does not have buyer role."})
                ]
            ),
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Favorite car not found or user does not have permission.",
                examples=[
                    OpenApiExample("Not Found", value={"detail": "Favorite car not found or you do not have permission to view it."})
                ]
            )
        }
    ),
    destroy=extend_schema(
        tags=["Favorites"],
        description="Remove a car from the user's favorites. User must be the owner and have the buyer role.",
        responses={
            204: None,
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have the buyer role.",
                examples=[
                    OpenApiExample("Forbidden", value={"detail": "User does not have buyer role."})
                ]
            ),
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Favorite car not found or user does not have permission.",
                examples=[
                    OpenApiExample("Not Found", value={"detail": "Favorite car not found or you do not have permission to delete it."})
                ]
            )
        }
    )
)
class FavoriteCarViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                         mixins.DestroyModelMixin, GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteCarSerializer
    queryset = FavoriteCar.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        favorites = FavoriteCarService.list_favorites(request.user, self.get_queryset())
        return Response(self.get_serializer(favorites, many=True).data)

    def create(self, request, *args, **kwargs):
        data = FavoriteCarService.create_favorite(
            user=request.user,
            data=request.data,
            serializer_class=self.get_serializer_class()
        )
        return Response(data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        data = FavoriteCarService.retrieve_favorite(
            user=request.user,
            pk=kwargs['pk'],
            queryset=self.get_queryset(),
            serializer_class=self.get_serializer_class()
        )
        return Response(data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        FavoriteCarService.destroy_favorite(
            user=request.user,
            pk=kwargs['pk'],
            queryset=self.get_queryset()
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema_view(
    create=extend_schema(
        tags=["Car Views"],
        description="Create a car view record for a specific car. Records the user (if authenticated) or IP address (if anonymous).",
        request=CarViewSerializer,
        responses={
            201: CarViewSerializer,
            400: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Invalid input, e.g., missing or invalid car_id.",
                examples=[
                    OpenApiExample("Invalid car_id", value={"error": "Invalid car_id"})
                ]
            )
        }
    ),
    list=extend_schema(
        tags=["Car Views"],
        description="List all car view records. Typically restricted to super admins or users with specific permissions.",
        responses={
            200: CarViewSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="User lacks permission to access this endpoint.",
                examples=[
                    OpenApiExample("Forbidden", value={"error": "You do not have permission to perform this action."})
                ]
            )
        }
    ),
    retrieve=extend_schema(
        tags=["Car Views"],
        description="Retrieve a specific car view record by ID. Typically restricted to super admins or users with specific permissions.",
        responses={
            200: CarViewSerializer,
            403: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="User lacks permission to access this endpoint.",
                examples=[
                    OpenApiExample("Forbidden", value={"error": "You do not have permission to perform this action."})
                ]
            ),
            404: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Car view not found.",
                examples=[
                    OpenApiExample("Not Found", value={"error": "Not found."})
                ]
            )
        }
    ),
    update=extend_schema(
        tags=["Car Views"],
        description="Updating car view records is not allowed.",
        responses={
            405: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Method not allowed.",
                examples=[
                    OpenApiExample("Method Not Allowed", value={"error": "Updating views is not allowed."})
                ]
            )
        }
    ),
    partial_update=extend_schema(
        tags=["Car Views"],
        description="Partially updating car view records is not allowed.",
        responses={
            405: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Method not allowed.",
                examples=[
                    OpenApiExample("Method Not Allowed", value={"error": "Updating views is not allowed."})
                ]
            )
        }
    ),
    destroy=extend_schema(
        tags=["Car Views"],
        description="Deleting car view records is not allowed.",
        responses={
            405: OpenApiResponse(
                response={"type": "object", "properties": {"error": {"type": "string"}}},
                description="Method not allowed.",
                examples=[
                    OpenApiExample("Method Not Allowed", value={"error": "Deleting views is not allowed."})
                ]
            )
        }
    ),
)
class CarViewViewSet(ModelViewSet):
    queryset = CarView.objects.all()
    serializer_class = CarViewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    http_method_names = ['get', 'post']  # Restrict to GET and POST only

    def perform_create(self, serializer):
        ip_address = self.request.META.get('REMOTE_ADDR')
        user = self.request.user if self.request.user.is_authenticated else None

        car = serializer.validated_data.get("car")
        car_view, created = CarView.objects.update_or_create(
            car=car,
            user=user,
            defaults={"ip_address": ip_address}
        )
        serializer.instance = car_view

    def update(self, request, *args, **kwargs):
        return Response({"error": "Updating views is not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response({"error": "Updating views is not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({"error": "Deleting views is not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

# OpenAPI schema for popular cars is provided via method-level schemas where needed.
class PopularCarsPagination(PageNumberPagination):
    """Pagination for popular cars list to avoid large payloads."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class PopularCarsViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet ):
    permission_classes = [AllowAny]
    serializer_class = CarListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['verification_status', 'sale_type', 'make_ref']
    search_fields = ['make', 'model', 'description']
    ordering_fields = ['views_count', 'price', 'created_at']
    ordering = ['-views_count']
    pagination_class = PopularCarsPagination

    @extend_schema(
        tags=["Popular Cars"],
        summary="List popular cars",
        description="Return verified cars ordered by popularity, with optional price filters.",
        responses={200: CarListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")

        return PopularCarService.get_popular_cars(
            min_price=min_price,
            max_price=max_price,
        )

    @extend_schema(
        tags=["Popular Cars"],
        summary="Retrieve a popular car",
        description="Return a popular car and increment its view count.",
        responses={200: CarListSerializer, 404: OpenApiResponse(description="Not found")},
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance = PopularCarService.increment_views(instance)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(
        tags=["Contacts"],
        summary="List all contacts (Admin only)",
        description="Retrieve all contact requests. Accessible only by admins.",
        responses={200: ContactSerializer(many=True)},
    ),

    retrieve=extend_schema(
        tags=["Contacts"],
        summary="Retrieve a contact",
        description="Retrieve details of a specific contact request by ID.",
        responses={
            200: ContactSerializer,
            404: OpenApiResponse(description="Contact not found"),
        },
    ),

    create=extend_schema(
        tags=["Contacts"],
        summary="Send contact request",
        description="""
        Create a contact request to a car owner, dealer, or broker.

        Rules:
        - Provide ONLY ONE of: `car_id`, `dealer_id`, or `broker_id`
        - Buyer must include phone number
        - Prevents duplicate contact per car
        - Rate limited (anti-spam protection)

        Notifications:
        - Sends notification to recipient (dealer/broker/user)
        """,
        request=inline_serializer(
            name="ContactRequest",
            fields={
                "phone": serializers.CharField(),
                "message": serializers.CharField(required=False),
                "car_id": serializers.IntegerField(required=False),
                "dealer_id": serializers.IntegerField(required=False),
                "broker_id": serializers.IntegerField(required=False),
            },
        ),
        responses={
            201: ContactSerializer,
            400: OpenApiResponse(description="Invalid input or duplicate request"),
            403: OpenApiResponse(description="Permission denied"),
        },
    ),
)
class ContactViewSet(CreateModelMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Contact.objects.select_related("sender", "recipient", "car")
    serializer_class = ContactSerializer
    permission_classes = [IsSuperAdminOrAdminOrBuyer]

    def get_serializer_context(self):
        return {"request": self.request}

    def create(self, request, *args, **kwargs):
        car_id = request.data.get("car_id")
        car = get_object_or_404(Car, id=car_id)
        dealer_id = request.data.get("dealer_id")
        broker_id = request.data.get("broker_id")

        logger.info(f"REQUEST USER: {request.user.id}")
        logger.info(f"CAR POSTED BY: {car.posted_by.id}")

        profile = ContactService.get_profile(
            car_id=car_id,
            dealer_id=dealer_id,
            broker_id=broker_id,
        )

        car = None
        if car_id:
            car = get_object_or_404(Car, id=car_id)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contact = serializer.save(
            sender=request.user,
            recipient=profile,
            car=car
        )

        ContactService.notify_contact_created(
            sender=request.user,
            recipient_profile=profile,
            contact=contact
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        ContactService.check_admin(request.user)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        # Now retrieves actual contact
        contact = self.get_object()
        serializer = self.get_serializer(contact)
        return Response(serializer.data)

