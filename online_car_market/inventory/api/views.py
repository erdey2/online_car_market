import logging
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework.exceptions import ValidationError

from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.filters import SearchFilter, OrderingFilter

from rolepermissions.checkers import has_role
from drf_spectacular.utils import (extend_schema, extend_schema_view, OpenApiParameter,
                                   OpenApiTypes, OpenApiExample, OpenApiResponse)
from ..models import Car, CarMake, CarModel, FavoriteCar, CarView
from .serializers import (
                          VerifyCarSerializer, CarMakeSerializer, ContactSerializer,
                          CarModelSerializer, FavoriteCarSerializer, CarViewSerializer,
                          CarWriteSerializer, CarListSerializer, CarDetailSerializer,
                          CarVerificationListSerializer, CarVerificationAnalyticsSerializer
                          )
from online_car_market.users.permissions.drf_permissions import IsSuperAdminOrAdmin, IsSuperAdminOrAdminOrBuyer
from online_car_market.users.permissions.business_permissions import CanPostCar
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.users.models import Profile
from online_car_market.bids.api.serializers import BidSerializer
from ..services.car_service import CarService
from ..services.car_filter_service import CarFilterService
from ..services.car_query_service import CarQueryService
from ..services.car_verification_service import CarVerificationService
from ..services.car_bid_service import CarBidService
from ..services.popular_car_service import PopularCarService

logger = logging.getLogger(__name__)

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

    @method_decorator(cache_page(60 * 60 * 12, key_prefix='car_makes_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]   # No authentication required
        return [IsSuperAdminOrAdmin()]   # Only admins for create/update/delete

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
        description=(
            "List cars. "
            "Unauthenticated users see only verified cars. "
            "Authenticated users (broker, seller, dealer, admin) "
            "may see additional cars depending on their role."
        ),
        parameters=[
            OpenApiParameter(
                name="broker_email",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter cars by broker email address.",
                required=False,
            ),
        ],
        responses={
            200: CarListSerializer(many=True),
        },
    ),
    retrieve=extend_schema(
        tags=["Dealers - Inventory"],
        description=(
            "Retrieve a specific car. "
            "Public users can only access verified cars. "
            "Authenticated users may access additional cars based on role."
        ),
        responses={
            200: CarDetailSerializer,
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Car not found or not accessible.",
                examples=[
                    OpenApiExample(
                        "Not Found",
                        value={"detail": "Not found."},
                    )
                ],
            ),
        },
    ),
    create=extend_schema(
        tags=["Dealers - Inventory"],
        description=(
            "Create a car listing. "
            "Allowed for dealers, sellers, brokers, and admins. "
            "Brokers must have `can_post=True`."
        ),
        request=CarWriteSerializer,
        responses={
            201: CarDetailSerializer,
            403: OpenApiResponse(description="Permission denied."),
        },
    ),

    update=extend_schema(
        tags=["Dealers - Inventory"],
        description="Fully update a car listing.",
        request=CarWriteSerializer,
        responses={200: CarDetailSerializer},
    ),

    partial_update=extend_schema(
        tags=["Dealers - Inventory"],
        description="Partially update a car listing.",
        request=CarWriteSerializer,
        responses={200: CarDetailSerializer},
    ),

    destroy=extend_schema(
        tags=["Dealers - Inventory"],
        description="Delete a car listing (dealers, brokers, admins only).",
        responses={204: None},
    ),
)
class CarViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == "list":
            return CarListSerializer
        if self.action == "retrieve":
            return CarDetailSerializer
        if self.action in ["create", "update", "partial_update"]:
            return CarWriteSerializer
        if self.action == "verify":
            return VerifyCarSerializer
        if self.action == "bid":
            return BidSerializer
        return CarListSerializer

    def get_queryset(self):
        if self.action == "list":
            qs = CarQueryService.for_list()
        elif self.action == "retrieve":
            qs = CarQueryService.for_detail()
        else:
            qs = CarQueryService.base_queryset()

        return CarQueryService.get_visible_cars_for_user(self.request.user, qs)

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), CanPostCar()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        car = CarService.create_car_with_images(
            serializer=serializer,
            request=request
        )

        return Response(
            CarDetailSerializer(car, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Dealers - Inventory"],
        parameters=[
            OpenApiParameter(name="fuel_type", type=OpenApiTypes.STR, location="query", description="Fuel type (electric, hybrid, petrol, diesel)"),
            OpenApiParameter(name="price_min", type=OpenApiTypes.FLOAT, location="query", description="Minimum price"),
            OpenApiParameter(name="price_max", type=OpenApiTypes.FLOAT, location="query", description="Maximum price"),
            OpenApiParameter(name="sale_type", type=OpenApiTypes.STR, location="query", description="Sale type (fixed_price, auction)"),
            OpenApiParameter(name="make_ref", type=OpenApiTypes.INT, location="query", description="Car make ID"),
            OpenApiParameter(name="model_ref", type=OpenApiTypes.INT, location="query", description="Car model ID"),
            OpenApiParameter(name="make", type=OpenApiTypes.STR, location="query", description="Car make name"),
            OpenApiParameter(name="model", type=OpenApiTypes.STR, location="query", description="Car model name"),
        ],
        description="Filter verified cars by fuel type, price range, sale type, make, or model, with verified cars prioritized.",
        responses={
            200: CarListSerializer(many=True),
            400: OpenApiResponse(description="Invalid filter parameters."),
        },
    )
    @action(detail=False, methods=['get'])
    def filter(self, request):
        queryset = CarQueryService.for_list()

        queryset = CarQueryService.get_visible_cars_for_user(
            request.user, queryset
        )
        try:
            filtered_queryset = CarFilterService.filter_cars(
                queryset=queryset,
                query_params=request.query_params
            )
        except ValidationError as e:
            return Response({"error": str(e.detail)}, status=400)

        serializer = CarListSerializer(
            filtered_queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @extend_schema(
        tags=["Dealers - Inventory"],
        description="Place a bid on an auction car.",
        request=BidSerializer,
        responses={201: BidSerializer}
    )
    @action(detail=True, methods=["post"])
    def bid(self, request, pk=None):
        car = self.get_object()

        serializer = BidSerializer(
            data=request.data,
            context={"request": request}
        )
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
            location=OpenApiParameter.QUERY,
            description="Filter by status: pending, verified, rejected",
            required=False,
        ),
    ],
    responses={200: CarVerificationListSerializer(many=True)},
)
)
class CarVerificationViewSet(viewsets.GenericViewSet):

    permission_classes = [IsAuthenticated]
    queryset = Car.objects.all()
    serializer_class = CarVerificationListSerializer

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
        detail=True, methods=["patch"], permission_classes=[IsAuthenticated, IsSuperAdminOrAdmin],
    )
    def verify(self, request, pk=None):
        car = self.get_object()

        serializer = VerifyCarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        car = CarVerificationService.verify_car(
            car=car,
            verification_status=serializer.validated_data["verification_status"],
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
        data = CarVerificationService.get_verification_analytics(
            request.user
        )

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
class UserCarsViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Car.objects.all()

    # Serializer selection
    def get_serializer_class(self):
        if self.action == "list":
            return CarListSerializer
        if self.action == "retrieve":
            return CarDetailSerializer
        return CarListSerializer

    # Role-based filtering
    def get_queryset(self):
        user = self.request.user
        qs = Car.objects.select_related(
            "dealer",
            "broker",
            "posted_by"
        ).prefetch_related("images", "bids")

        # Admin / Super Admin -> full access
        if has_role(user, ["super_admin", "admin"]):
            return qs

        # Dealer -> all cars under dealership
        if hasattr(user, "profile") and hasattr(user.profile, "dealer_profile"):
            return qs.filter(dealer=user.profile.dealer_profile)

        # Broker -> their own cars
        if hasattr(user, "profile") and hasattr(user.profile, "broker_profile"):
            return qs.filter(broker=user.profile.broker_profile)

        # Seller -> only cars they posted under assigned dealer
        seller_record = user.dealer_staff_assignments.filter(role="seller").first()
        if seller_record:
            return qs.filter(
                dealer=seller_record.dealer,
                posted_by=user
            )

        # No valid role -> empty queryset
        return qs.none()

    # Extra permission guard (cleaned)
    def _has_inventory_access(self, user):
        return (
            has_role(user, ["super_admin", "admin", "dealer", "broker"]) or
            user.dealer_staff_assignments.filter(role="seller").exists()
        )

    def list(self, request, *args, **kwargs):
        if not self._has_inventory_access(request.user):
            return Response(
                {"detail": "You do not have permission to view cars."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if not self._has_inventory_access(request.user):
            return Response(
                {"detail": "You do not have permission to view this car."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().retrieve(request, *args, **kwargs)

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
class FavoriteCarViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FavoriteCarSerializer
    queryset = FavoriteCar.objects.all()

    def get_queryset(self):
        # Restrict to favorites by the authenticated user
        return self.queryset.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            favorite = self.get_queryset().get(pk=kwargs['pk'])
            serializer = self.get_serializer(favorite)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except FavoriteCar.DoesNotExist:
            return Response(
                {"detail": "Favorite car not found or you do not have permission to view it."},
                status=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            favorite = self.get_queryset().get(pk=kwargs['pk'])
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except FavoriteCar.DoesNotExist:
            return Response(
                {"detail": "Favorite car not found or you do not have permission to delete it."},
                status=status.HTTP_404_NOT_FOUND
            )

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
class CarViewViewSet(viewsets.ModelViewSet):
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

@extend_schema_view(
    list=extend_schema(
        tags=["Popular Cars"],
        description="List popular cars based on view count. Accessible to all users, including buyers and unauthenticated users.",
        parameters=[
            OpenApiParameter(
                name='status',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by car status (pending, verified, rejected)',
                enum=['pending', 'verified', 'rejected']
            ),
            OpenApiParameter(
                name='sale_type',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Filter by sale type (direct, auction)',
                enum=['direct', 'auction']
            ),
            OpenApiParameter(
                name='make_ref',
                type=int,
                location=OpenApiParameter.QUERY,
                description='Filter by car make ID'
            ),
            OpenApiParameter(
                name='min_price',
                type=float,
                location=OpenApiParameter.QUERY,
                description='Filter by minimum price'
            ),
            OpenApiParameter(
                name='max_price',
                type=float,
                location=OpenApiParameter.QUERY,
                description='Filter by maximum price'
            ),
            OpenApiParameter(
                name='search',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Search by make, model, or description'
            ),
            OpenApiParameter(
                name='ordering',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Order by views, price, or created_at (prefix with - for descending)',
                enum=['views', '-views', 'price', '-price', 'created_at', '-created_at']
            )
        ],
        responses={
            200: CarListSerializer(many=True),
        }
    ),
    retrieve=extend_schema(
        tags=["Popular Cars"],
        description="Retrieve details of a specific popular car. Increments view count. Accessible to all users, including buyers and unauthenticated users.",
        responses={
            200: CarListSerializer,
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Car not found.",
                examples=[
                    OpenApiExample("Not Found", value={"detail": "Car not found."})
                ]
            )
        }
    )
)
class PopularCarsViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet ):
    permission_classes = [AllowAny]
    serializer_class = CarListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'sale_type', 'make_ref']
    search_fields = ['make', 'model', 'description']
    ordering_fields = ['views', 'price', 'created_at']
    ordering = ['-views']

    def get_queryset(self):
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")

        return PopularCarService.get_popular_cars(
            min_price=min_price,
            max_price=max_price,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance = PopularCarService.increment_views(instance)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Inventory"],
        description="List all contacts (admin-only).",
        responses={200: ContactSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Dealers - Inventory"],
        description=(
            "Retrieve the contact info of the user associated with a specific car, "
            "dealer, or broker. Accessible to authenticated users (buyers) or admins."
        ),
        parameters=[
            OpenApiParameter(
                name="car_id",
                type=int,
                location="path",
                description="ID of the car to get the poster's profile",
                required=False,
            ),
            OpenApiParameter(
                name="dealer_id",
                type=int,
                location="query",
                description="ID of the dealer to get contact info",
                required=False,
            ),
            OpenApiParameter(
                name="broker_id",
                type=int,
                location="query",
                description="ID of the broker to get contact info",
                required=False,
            ),
        ],
        responses={
            200: ContactSerializer,
            404: OpenApiResponse(description="Car, dealer, or broker not found"),
            403: OpenApiResponse(description="Permission denied"),
        },
    ),
)
class ContactViewSet(ReadOnlyModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsSuperAdminOrAdminOrBuyer]

    def list(self, request, *args, **kwargs):
        """Admin-only list of all contacts."""
        user = request.user
        if not (user.is_staff or getattr(user, "is_super_admin", False)):
            return Response({"detail": "Only admins can list all contacts"}, status=status.HTTP_403_FORBIDDEN,)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        car_id = kwargs.get("pk")  # From URL path
        dealer_id = request.query_params.get("dealer_id")
        broker_id = request.query_params.get("broker_id")

        # Validate input
        if not any([car_id, dealer_id, broker_id]):
            return Response(
                {"detail": "Please provide car_id, dealer_id, or broker_id"}, status=status.HTTP_400_BAD_REQUEST,)
        if sum(bool(x) for x in [car_id, dealer_id, broker_id]) > 1:
            return Response({"detail": "Please provide only one of car_id, dealer_id, or broker_id"},
                            status=status.HTTP_400_BAD_REQUEST,
            )
        # Retrieve profile
        if car_id:
            car = get_object_or_404(Car, id=car_id)
            profile = car.posted_by.profile
        elif dealer_id:
            dealer = get_object_or_404(DealerProfile, id=dealer_id)
            profile = dealer.profile
        elif broker_id:
            broker = get_object_or_404(BrokerProfile, id=broker_id)
            profile = broker.profile
        else:
            return Response({"detail": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(profile)
        return Response(serializer.data)
