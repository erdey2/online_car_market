import logging
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, inline_serializer
from .serializers import (UserRoleSerializer, ProfileSerializer, UserSerializer,
                          ERPLoginSerializer, AdminLoginSerializer, BuyerRegisterSerializer,
                          BrokerRegisterSerializer, DealerRegisterSerializer, UserFullSerializer)
from online_car_market.users.permissions.drf_permissions import IsSuperAdminOrAdmin
from rest_framework.decorators import action
from dj_rest_auth.views import LoginView
from ..services.profile_service import ProfileService
from ..services.user_service import UserService

User = get_user_model()
logger = logging.getLogger(__name__)

class AuthViewSet(ViewSet):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Register as Buyer",
        description="""
        Create a new buyer account.

        Creates:
        - User
        - Profile

        Optional fields:
        - first_name
        - last_name
        - contact
        - description
        """,
        request=BuyerRegisterSerializer,
        responses={
            201: OpenApiResponse(
                description="Buyer registered successfully"
            ),
            400: OpenApiResponse(
                description="Validation error"
            ),
        },
    )
    @action(detail=False, methods=["post"])
    def register_buyer(self, request):
        serializer = BuyerRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"detail": "Buyer registered successfully"}, status=201 )

    @extend_schema(
        tags=["Authentication"],
        summary="Register as Broker",
        description="""
            Register a new broker.

            - Creates User + Profile + BrokerProfile
            - Broker status will be **PENDING**
            - Requires admin approval before activation
            """,
        request=inline_serializer(
            name="BrokerRegisterRequest",
            fields={
                "email": serializers.EmailField(),
                "password": serializers.CharField(),
                "national_id": serializers.CharField(),
                "telebirr_account": serializers.CharField(),
            },
        ),
        responses={
            201: OpenApiResponse(description="Broker registered. Awaiting approval"),
            400: OpenApiResponse(description="Invalid input"),
        },
    )
    @action(detail=False, methods=["post"])
    def register_broker(self, request):
        serializer = BrokerRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Broker registered. Awaiting approval"}, status=201)

    @extend_schema(
        tags=["Authentication"],
        summary="Register as Dealer",
        description="""
            Register a new dealer.

            - Creates User + Profile + DealerProfile
            - Dealer status will be **PENDING**
            - Requires admin approval before activation
            """,
        request=inline_serializer(
            name="DealerRegisterRequest",
            fields={
                "email": serializers.EmailField(),
                "password": serializers.CharField(),
                "company_name": serializers.CharField(),
                "license_number": serializers.CharField(),
                "tax_id": serializers.CharField(required=False),
                "telebirr_account": serializers.CharField(required=False),
                "business_license": serializers.FileField(),
            },
        ),
        responses={
            201: OpenApiResponse(description="Dealer registered. Awaiting approval"),
            400: OpenApiResponse(description="Invalid input"),
        },
    )
    @action(detail=False, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def register_dealer(self, request):
        serializer = DealerRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Dealer registered. Awaiting approval"}, status=201)

    @extend_schema(
        tags=["Authentication"],
        summary="Create Admin (Super Admin only)",
        description="Only super admins can create admin users.",
        request=inline_serializer(
            name="AdminRegisterRequest",
            fields={
                "email": serializers.EmailField(),
                "password": serializers.CharField(),
            },
        ),
        responses={201: OpenApiResponse(description="Admin created successfully")},
    )
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def create_admin(self, request):

        if not (request.user.is_superuser or request.user.role == "super_admin"):
            return Response(
                {"detail": "Only super admins can create admins."},
                status=403
            )

        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {"detail": "Email and password are required."},
                status=400
            )

        user = User.objects.create_user(
            email=email,
            password=password,
            role="admin",
            is_staff=True
        )

        return Response(
            {"detail": "Admin created successfully"},
            status=201
        )

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Users"],
        summary="Get current authenticated user",
        description="Retrieve the authenticated user's full info: User + Profile + Dealer/Broker profile (only relevant role).",
        responses={
            200: UserFullSerializer,
            401: OpenApiResponse(description="Authentication credentials were not provided"),
        },
    )
    def get(self, request):
        user = request.user
        serializer = UserFullSerializer(user)
        return Response(serializer.data)

class UserViewSet(ReadOnlyModelViewSet):
    """
    Admin endpoint to list and retrieve all users with full profiles.
    """
    queryset = User.objects.all().select_related(
        'profile', 'profile__broker_profile', 'profile__dealer_profile'
    )
    serializer_class = UserFullSerializer
    permission_classes = [IsSuperAdminOrAdmin]

    @extend_schema(
        tags=["Users"],
        summary="List all users",
        description="Admin endpoint to list all users with full profiles. Only relevant role profile is included.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["Users"],
        summary="Retrieve a specific user",
        description="Admin endpoint to retrieve a single user by ID with full profile. Only relevant role profile is included.",
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

@extend_schema_view(
    list=extend_schema(tags=["Authentication & Users"]),
    retrieve=extend_schema(tags=["Authentication & Users"]),
    partial_update=extend_schema(tags=["Authentication & Users"]),
    me=extend_schema(tags=["Authentication & Users"]),
)
class ProfileViewSet(ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch']

    def get_queryset(self):
        return ProfileService.get_visible_profiles(self.request.user)

    def retrieve(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile)
        logger.info(f"Profile retrieved for {request.user.email}")
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    @extend_schema(
        summary="Get or update your own profile",
        responses=ProfileSerializer,
    )
    def me(self, request):
        profile = ProfileService.get_my_profile(request.user)
        if not profile:
            return Response({"detail": "Profile not found."}, status=404)

        if request.method == "GET":
            return Response(self.get_serializer(profile).data)
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_profile = ProfileService.update_profile(
            profile, serializer.validated_data
        )

        logger.info(f"Profile (me) updated for {request.user.email}")
        return Response(self.get_serializer(updated_profile).data)

@extend_schema_view(
    create=extend_schema(
        tags=["Authentication & Users"],
        summary="Assign a role to a user",
        request=UserRoleSerializer,
        responses={200: UserRoleSerializer},
    )
)
class UserRoleViewSet(ViewSet):
    permission_classes = [IsSuperAdminOrAdmin]

    def create(self, request):
        serializer = UserRoleSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info(
            f"Role assigned to {user.email}: {serializer.validated_data['role']}"
        )
        return Response(serializer.data)

@extend_schema_view(
    list=extend_schema(
        tags=["Authentication & Users"],
        summary="List all buyers (user-level info)",
        responses={200: UserSerializer(many=True)},
    )
)
class BuyerUserViewSet(ReadOnlyModelViewSet):
    """ViewSet to list all buyers (user-level info)"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsSuperAdminOrAdmin]
    http_method_names = ['get']

    def get_queryset(self):
        """Return all users with the 'buyer' role"""
        return UserService.get_buyers()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        logger.info(f"{request.user.email} retrieved the list of buyers (user-level).")
        return Response(serializer.data)

class ERPLoginView(LoginView):
    serializer_class = ERPLoginSerializer

class AdminLoginView(LoginView):
    serializer_class = AdminLoginSerializer



