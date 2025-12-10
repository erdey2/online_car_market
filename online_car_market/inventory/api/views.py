import logging
from django.db.models import Q, Avg
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils.decorators import method_decorator

from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions, mixins
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.filters import SearchFilter, OrderingFilter

from rolepermissions.checkers import has_role
from drf_spectacular.utils import (extend_schema, extend_schema_view, OpenApiParameter,
                                   OpenApiTypes, OpenApiExample, OpenApiResponse)
from ..models import Car, CarMake, CarModel, FavoriteCar, CarView, CarImage, Inspection
from .serializers import (CarSerializer, VerifyCarSerializer, BidSerializer, CarMakeSerializer, ContactSerializer,
                          CarModelSerializer, FavoriteCarSerializer, CarViewSerializer, InspectionSerializer
                          )
from online_car_market.users.permissions.drf_permissions import IsSuperAdminOrAdmin, IsSuperAdminOrAdminOrBuyer, IsBrokerOrSeller
from online_car_market.users.permissions.business_permissions import CanPostCar
from online_car_market.dealers.models import DealerProfile
from online_car_market.brokers.models import BrokerProfile
from online_car_market.users.models import Profile
from online_car_market.users.permissions.business_permissions import IsAdminOrReadOnly

logger = logging.getLogger(__name__)

CACHE_KEY_MAKES = "car_makes_list"
CACHE_KEY_MODELS = "car_models_list"
CACHE_KEY_CARS = "car_list"

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

    @receiver([post_save, post_delete], sender=CarMake)
    def refresh_car_make_cache(sender, instance, **kwargs):
        queryset = list(CarMake.objects.values("id", "name"))
        cache.set(CACHE_KEY_MAKES, queryset, 60 * 60 * 12)

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

    @method_decorator(cache_page(60 * 60 * 12, key_prefix="car_models_list"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @receiver([post_save, post_delete], sender=CarModel)
    def refresh_car_model_cache(sender, instance, **kwargs):
        queryset = list(CarModel.objects.select_related("make").values("id", "name", "make__id", "make__name"))
        cache.set(CACHE_KEY_MODELS, queryset, 60 * 60 * 12)

@extend_schema_view(
list=extend_schema(
        tags=["Dealers - Inventory"],
        description="List all verified cars for any user. Authenticated users with roles (broker, seller, dealer, admin) see additional cars based on their role.",
        parameters=[
            OpenApiParameter(
                name='broker_email',
                type=str,
                location='query',
                description='Filter cars by broker email address.',
                required=False
            ),
        ],
        responses={
            200: CarSerializer(many=True),
        }
    ),
    retrieve=extend_schema(
        tags=["Dealers - Inventory"],
        description="Retrieve a specific verified car for any user. Authenticated users with roles can access additional cars.",
        responses={
            200: CarSerializer,
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Car not found or not accessible.",
                examples=[OpenApiExample("Not Found", value={"detail": "Not found."})]
            )
        }
    ),
    create=extend_schema(
        tags=["Dealers - Inventory"],
        description="Create a car listing (dealers/brokers/seller/admins only). Brokers must have paid (can_post=True).",
        request=CarSerializer,
        responses={201: CarSerializer}
    ),
    update=extend_schema(
        tags=["Dealers - Inventory"],
        description="Update a car listing (dealers/brokers/admins only).",
        request=CarSerializer,
        responses={200: CarSerializer}
    ),
    partial_update=extend_schema(
        tags=["Dealers - Inventory"],
        description="Partially update a car listing.",
        request=CarSerializer,
        responses={200: CarSerializer}
    ),
    destroy=extend_schema(
        tags=["Dealers - Inventory"],
        description="Delete a car listing (dealers/brokers/admins only).",
        responses={204: None}
    ),
)
class CarViewSet(viewsets.ModelViewSet):
    serializer_class = CarSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & CanPostCar]
    parser_classes = [MultiPartParser, FormParser]

    @method_decorator(cache_page(60 * 60 * 15, key_prefix='car_list'))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @receiver([post_save, post_delete], sender=Car)
    def refresh_car_list_cache(sender, instance, **kwargs):
        queryset = list(Car.objects.all())
        cache.set(CACHE_KEY_CARS, queryset, 60 * 60 * 12)

    def get_queryset(self):
        user = self.request.user

        qs = (Car.objects.select_related(
                "dealer", "dealer__profile", "dealer__profile__user",
                "broker", "broker__profile", "broker__profile__user",
                "posted_by"
            )
            .prefetch_related(
                "images",  # Car.images (reverse FK)
                "bids",  # Car.bids (reverse FK)
            )
            # annotate dealer/broker average rating (one DB aggregate per result set, not per instance)
            .annotate(dealer_avg=Avg("dealer__ratings__rating"), broker_avg=Avg("broker__ratings__rating"))
            .order_by("-priority", "-created_at")
        )

        # Role filters
        if has_role(user, ["super_admin", "admin"]):
            pass
        elif has_role(user, "dealer"):
            qs = qs.filter(dealer__profile__user=user)
        elif has_role(user, "seller"):
            qs = qs.filter(posted_by=user)
        elif has_role(user, "broker"):
            qs = qs.filter(broker__profile__user=user)
        else:
            qs = qs.filter(verification_status="verified")

        # broker_email as a single filter join — NO extra get() query
        broker_email = self.request.query_params.get("broker_email")
        if broker_email:
            qs = qs.filter(broker__profile__user__email=broker_email)

        return qs

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "bid", "pay", "broker_payment"]:
            return [CanPostCar()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        # 1. Broker role check
        if has_role(request.user, 'broker'):
            try:
                broker_profile = BrokerProfile.objects.get(profile__user=request.user)
                if not broker_profile.can_post:
                    return Response(
                        {"detail": "Broker must complete payment to post cars."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except BrokerProfile.DoesNotExist:
                return Response(
                    {"detail": "Broker profile not found."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 2. Save main car data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        car = serializer.save()

        # 3. Process uploaded images
        uploaded_images = []
        for key, file in request.FILES.items():
            if key.startswith("uploaded_images"):
                # Example key: uploaded_images[0].image_file
                index = key.split('[')[1].split(']')[0]
                caption = request.data.get(f"uploaded_images[{index}].caption")
                is_featured = request.data.get(f"uploaded_images[{index}].is_featured", "false").lower() == "true"
                uploaded_images.append({"image_file": file, "caption": caption, "is_featured": is_featured })

        # 4. Save CarImage instances
        first_image_id = None
        for i, img_data in enumerate(uploaded_images):
            car_image = CarImage.objects.create(car=car, image=img_data['image_file'], caption=img_data['caption'],
                                                is_featured=img_data['is_featured'] )
            if i == 0:
                first_image_id = car_image.id

        # 5. Ensure at least one featured image
        if not CarImage.objects.filter(car=car, is_featured=True).exists() and first_image_id:
            first_image = CarImage.objects.get(id=first_image_id)
            first_image.is_featured = True
            first_image.save()

        # 6. Return full car data
        return Response(self.get_serializer(car).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Dealers - Inventory"],
        description="Verify a car listing and set priority (admin/super_admin only).",
        request=VerifyCarSerializer,
        responses={200: VerifyCarSerializer}
    )
    @action(detail=True, methods=['patch'], serializer_class=VerifyCarSerializer,
            parser_classes=[JSONParser, FormParser, MultiPartParser])
    def verify(self, request, pk=None):
        if not has_role(request.user, ['super_admin', 'admin']):
            return Response(
                {"detail": "Only admins can verify cars."},
                status=status.HTTP_403_FORBIDDEN
            )
        car = self.get_object()
        serializer = self.get_serializer(car, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        verification_status = serializer.validated_data.get('verification_status')
        if verification_status is None:
            return Response(
                {"error": "verification_status is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        car.verification_status = verification_status
        car.priority = (car.verification_status == 'verified')
        car.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

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
        responses={200: CarSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], serializer_class=CarSerializer)
    def filter(self, request):
        queryset = self.get_queryset()
        fuel_type = request.query_params.get('fuel_type')
        price_min = request.query_params.get('price_min')
        price_max = request.query_params.get('price_max')
        sale_type = request.query_params.get('sale_type')
        make_ref = request.query_params.get('make_ref')
        model_ref = request.query_params.get('model_ref')
        make = request.query_params.get('make')
        model = request.query_params.get('model')

        valid_fuel_types = [choice[0] for choice in Car.FUEL_TYPES]
        if fuel_type and fuel_type not in valid_fuel_types:
            return Response(
                {"error": f"Invalid fuel type. Must be one of: {', '.join(valid_fuel_types)}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        valid_sale_types = [choice[0] for choice in Car.SALE_TYPES]
        if sale_type and sale_type not in valid_sale_types:
            return Response(
                {"error": f"Invalid sale type. Must be one of: {', '.join(valid_sale_types)}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if fuel_type:
            queryset = queryset.filter(fuel_type=fuel_type)
        if make_ref:
            try:
                make_ref = int(make_ref)
                if not CarMake.objects.filter(id=make_ref).exists():
                    return Response({"error": "Invalid make ID."}, status=status.HTTP_400_BAD_REQUEST)
                queryset = queryset.filter(make_ref=make_ref)
            except ValueError:
                return Response({"error": "Make ID must be a valid integer."}, status=status.HTTP_400_BAD_REQUEST)
        if model_ref:
            try:
                model_ref = int(model_ref)
                if not CarModel.objects.filter(id=model_ref).exists():
                    return Response({"error": "Invalid model ID."}, status=status.HTTP_400_BAD_REQUEST)
                queryset = queryset.filter(model_ref=model_ref)
            except ValueError:
                return Response({"error": "Model ID must be a valid integer."}, status=status.HTTP_400_BAD_REQUEST)
        if make:
            if not CarMake.objects.filter(name__iexact=make).exists():
                return Response({"error": "Invalid make name."}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(Q(make=make) | Q(make_ref__name__iexact=make))
        if model:
            if not CarModel.objects.filter(name__iexact=model).exists():
                return Response({"error": "Invalid model name."}, status=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(Q(model=model) | Q(model_ref__name__iexact=model))
        try:
            if price_min:
                price_min = float(price_min)
                if price_min < 0:
                    return Response({"error": "Minimum price cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
                queryset = queryset.filter(price__gte=price_min)
            if price_max:
                price_max = float(price_max)
                if price_max < 0:
                    return Response({"error": "Maximum price cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
                if price_min and price_max < price_min:
                    return Response(
                        {"error": "Maximum price cannot be less than minimum price."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                queryset = queryset.filter(price__lte=price_max)
        except ValueError:
            return Response({"error": "Price parameters must be valid numbers."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Dealers - Inventory"],
        description="Place a bid on an auction car.",
        request=BidSerializer,
        responses={201: BidSerializer}
    )
    @action(detail=True, methods=['post'], serializer_class=BidSerializer)
    def bid(self, request, pk=None):
        car = self.get_object()
        if car.sale_type != 'auction':
            return Response(
                {"detail": "Bids can only be placed on auction cars."},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        bid = serializer.save(car=car)
        return Response(BidSerializer(bid).data, status=status.HTTP_201_CREATED)

@extend_schema_view(
    list=extend_schema(
        tags=["User Cars"],
        description="List all cars belonging to the authenticated dealer, broker, or seller.",
        responses={
            200: CarSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have permission.",
            )
        }
    ),
    retrieve=extend_schema(
        tags=["User Cars"],
        description="Retrieve a specific car belonging to the authenticated dealer, broker, or seller.",
        responses={
            200: CarSerializer,
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User does not have permission.",
            ),
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Car not found or user does not have permission.",
            )
        }
    )
)
class UserCarsViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CarSerializer
    queryset = Car.objects.all()

    def get_queryset(self):
        user = self.request.user
        queryset = Car.objects.all()

        # 1. Super admin / admin: full access
        if has_role(user, ['super_admin', 'admin']):
            return queryset

        # 2. Dealer: see all cars under the dealership
        if hasattr(user, 'profile') and hasattr(user.profile, 'dealer_profile'):
            dealer = user.profile.dealer_profile
            return queryset.filter(dealer=dealer)

        # 3. Broker: see cars posted by the broker
        if hasattr(user, 'profile') and hasattr(user.profile, 'broker_profile'):
            broker = user.profile.broker_profile
            return queryset.filter(broker=broker)

        # 4. Seller: must be assigned under a dealer and sees only cars they posted
        seller_record = user.dealer_staff_assignments.filter(role='seller').first()
        if seller_record:
            dealer = seller_record.dealer
            return queryset.filter(dealer=dealer, posted_by=user)

        # 5. Default: public view (only verified + available)
        return queryset.filter(
            verification_status='verified',
            status='available'
        )

    def list(self, request, *args, **kwargs):
        # Sellers, dealers, brokers, admins are allowed
        if (
            not has_role(request.user, ['super_admin', 'admin', 'dealer', 'broker']) and
            not request.user.dealer_staff_assignments.filter(role='seller').exists()
        ):
            return Response({"detail": "You do not have permission to view cars."}, status=status.HTTP_403_FORBIDDEN)

        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if (
            not has_role(request.user, ['super_admin', 'admin', 'dealer', 'broker']) and
            not request.user.dealer_staff_assignments.filter(role='seller').exists()
        ):
            return Response(
                {"detail": "You do not have permission to view this car."}, status=status.HTTP_403_FORBIDDEN )
        try:
            car = self.get_queryset().get(pk=kwargs['pk'])
            serializer = self.get_serializer(car)
            return Response(serializer.data)
        except Car.DoesNotExist:
            return Response(
                {"detail": "Car not found or you do not have permission to view it."}, status=status.HTTP_404_NOT_FOUND
            )

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
            200: CarSerializer(many=True),
        }
    ),
    retrieve=extend_schema(
        tags=["Popular Cars"],
        description="Retrieve details of a specific popular car. Increments view count. Accessible to all users, including buyers and unauthenticated users.",
        responses={
            200: CarSerializer,
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
class PopularCarsViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]  # Public access
    serializer_class = CarSerializer
    queryset = Car.objects.filter(verification_status='verified')  # Only verified cars
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'sale_type', 'make_ref']
    search_fields = ['make', 'model', 'description']
    ordering_fields = ['views', 'price', 'created_at']
    ordering = ['-views']

    def get_queryset(self):
        """
        Return verified cars ordered by view count, with optional filtering.
        """
        queryset = self.queryset

        # Apply additional filters
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        return queryset.order_by('-views')

    def list(self, request, *args, **kwargs):
        """
        List popular cars based on view count with pagination and filtering.
        """
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific car and increment its view count.
        """
        try:
            instance = self.get_object()
            instance.views += 1
            instance.save(update_fields=['views'])
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Car.DoesNotExist:
            return Response({"detail": "Car not found."}, status=status.HTTP_404_NOT_FOUND)

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

@extend_schema_view(
    list=extend_schema(
        tags=["Car Inspections"],
        summary="List all inspections",
        description="Retrieve a list of all inspections. Admins see all, while brokers/sellers see their own.",
        responses={200: InspectionSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Car Inspections"],
        summary="Retrieve a specific inspection",
        description="Get detailed information about a specific inspection record.",
        responses={200: InspectionSerializer},
    ),
    create=extend_schema(
        tags=["Car Inspections"],
        summary="Create a new inspection",
        description="Allows a broker or seller to create a new inspection for a car.",
        request=InspectionSerializer,
        examples=[
            OpenApiExample(
                "Example Request",
                value={
                    "car_id": 12,
                    "inspected_by": "Top Garage Motors",
                    "inspection_date": "2025-11-10",
                    "remarks": "Engine and brakes are in excellent condition.",
                    "condition_status": "excellent"
                },
            ),
        ],
        responses={
            201: OpenApiResponse(response=InspectionSerializer, description="Inspection created successfully"),
            403: OpenApiResponse(description="Permission denied"),
        },
    ),
    update=extend_schema(
        tags=["Car Inspections"],
        summary="Update an inspection",
        description="Allows brokers or sellers to update an existing inspection they created.",
        responses={
            200: InspectionSerializer,
            403: OpenApiResponse(description="Permission denied"),
        },
    ),
    partial_update=extend_schema(
        tags=["Car Inspections"],
        summary="Partially update an inspection",
        description="Allows brokers or sellers to partially update fields of an existing inspection.",
    ),
    destroy=extend_schema(
        tags=["Car Inspections"],
        summary="Delete an inspection",
        description="Allows only admins to delete an inspection.",
        responses={204: OpenApiResponse(description="Deleted successfully")},
    ),
)
class InspectionViewSet(viewsets.ModelViewSet):
    queryset = Inspection.objects.select_related("car", "uploaded_by", "verified_by")
    serializer_class = InspectionSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update"]:
            return [IsBrokerOrSeller()]
        elif self.action in ["verify", "destroy"]:
            return [permissions.IsAdminUser()]
        else:
            return [IsAdminOrReadOnly()]

    def get_queryset(self):
        user = self.request.user

        if has_role(user, ["admin", "superadmin"]):
            return Inspection.objects.all()
        return Inspection.objects.filter(uploaded_by=user)

    @extend_schema(
        description="Verify or reject an inspection."
                    "This endpoint allows an **admin or superadmin** to update the inspection status "
                    "to either `'verified'` or `'rejected'`. Optionally, an admin can include remarks.",
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                required=True,
                description="The new status. Must be either 'verified' or 'rejected'."
            ),
            OpenApiParameter(
                name="admin_remarks",
                type=str,
                required=False,
                description="Optional remarks from the admin."
            ),
        ],
        responses={
            200: OpenApiResponse(description="Inspection verified or rejected successfully."),
            400: OpenApiResponse(description="Invalid status or bad request."),
            403: OpenApiResponse(description="Forbidden – user not authorized."),
            404: OpenApiResponse(description="Inspection not found."),
        },
    )
    @action(detail=True, methods=["patch"], permission_classes=[IsSuperAdminOrAdmin])
    def verify(self, request, pk=None):
        """Custom endpoint for admins to verify/reject inspections."""
        inspection = self.get_object()
        status_value = request.data.get("status")
        admin_remarks = request.data.get("admin_remarks", "")

        if status_value not in ["verified", "rejected"]:
            return Response({"error": "Invalid status. Must be 'verified' or 'rejected'."}, status=status.HTTP_400_BAD_REQUEST,)
        inspection.status = status_value
        inspection.verified_by = request.user
        inspection.verified_at = timezone.now()
        inspection.admin_remarks = admin_remarks
        inspection.save()

        return Response({"detail": f"Inspection {status_value} successfully."}, status=status.HTTP_200_OK,)
