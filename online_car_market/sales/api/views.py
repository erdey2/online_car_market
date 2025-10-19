from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status
from rolepermissions.permissions import register_object_checker
from rolepermissions.checkers import has_role
from online_car_market.sales.models import Sale, Lead
from online_car_market.dealers.models import DealerStaff
from .serializers import SaleSerializer, LeadSerializer
from online_car_market.brokers.models import BrokerProfile
from online_car_market.dealers.models import DealerProfile
from online_car_market.buyers.models import BuyerProfile
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample

class CanManageSales(BasePermission):
    """Only super_admin, admin, broker, or dealer can manage sales."""
    def has_permission(self, request, view):
        return has_role(request.user, ['super_admin', 'admin', 'broker', 'dealer', 'seller'])

@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Sales"],
        description="List sales based on user role: buyers see their purchases, brokers see their sales, dealers see their sales, admins see all.",
        responses={
            200: SaleSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User lacks permission.",
                examples=[OpenApiExample("Forbidden", value={"detail": "You do not have permission to perform this action."})]
            )
        }
    ),
    retrieve=extend_schema(
        tags=["Dealers - Sales"],
        description="Retrieve a specific sale if user is the buyer, broker, dealer, or admin.",
        responses={
            200: SaleSerializer,
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Sale not found.",
                examples=[OpenApiExample("Not Found", value={"detail": "Not found."})]
            )
        }
    ),
    create=extend_schema(
        tags=["Dealers - Sales"],
        description="Create a sale (brokers for their cars, dealers for their cars, admins).",
        request=SaleSerializer,
        responses={
            201: SaleSerializer,
            400: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Invalid input.",
                examples=[OpenApiExample("Invalid input", value={"detail": "Invalid data."})]
            ),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User lacks permission.",
                examples=[OpenApiExample("Forbidden", value={"detail": "Only brokers, dealers, or admins can create sales."})]
            )
        }
    ),
    update=extend_schema(
        tags=["Dealers - Sales"],
        description="Update a sale (brokers for their cars, dealers for their cars, admins).",
        request=SaleSerializer,
        responses={200: SaleSerializer}
    ),
    partial_update=extend_schema(
        tags=["Dealers - Sales"],
        description="Partially update a sale.",
        request=SaleSerializer,
        responses={200: SaleSerializer}
    ),
    destroy=extend_schema(
        tags=["Dealers - Sales"],
        description="Delete a sale (brokers for their cars, dealers for their cars, admins).",
        responses={204: None}
    ),
)
class SaleViewSet(ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageSales()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if has_role(user, ['super_admin', 'admin']):
            return self.queryset

        elif has_role(user, 'broker'):
            try:
                broker_profile = BrokerProfile.objects.get(profile__user=user)
                return self.queryset.filter(broker=broker_profile)
            except BrokerProfile.DoesNotExist:
                return self.queryset.none()

        elif has_role(user, 'dealer'):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
                return self.queryset.filter(car__dealer=dealer_profile)
            except DealerProfile.DoesNotExist:
                return self.queryset.none()

        elif has_role(user, 'seller'):
            try:
                # Assuming Seller is linked via DealerStaff (or directly to dealer)
                dealer_staff = DealerStaff.objects.get(user=user)
                return self.queryset.filter(car__dealer=dealer_staff.dealer)
            except DealerStaff.DoesNotExist:
                return self.queryset.none()

        elif has_role(user, 'buyer'):
            try:
                buyer_profile = BuyerProfile.objects.get(profile__user=user)
                return self.queryset.filter(buyer=buyer_profile.profile.user)
            except BuyerProfile.DoesNotExist:
                return self.queryset.none()

        return self.queryset.none()


@extend_schema_view(
    list=extend_schema(
        tags=["Dealers - Sales"],
        description="List leads based on user role: brokers/dealers see leads for their cars, admins see all.",
        responses={
            200: LeadSerializer(many=True),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User lacks permission.",
                examples=[OpenApiExample("Forbidden", value={"detail": "You do not have permission to perform this action."})]
            )
        }
    ),
    retrieve=extend_schema(
        tags=["Dealers - Sales"],
        description="Retrieve a specific lead if user is the assigned broker/dealer or admin.",
        responses={
            200: LeadSerializer,
            404: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Lead not found.",
                examples=[OpenApiExample("Not Found", value={"detail": "Not found."})]
            )
        }
    ),
    create=extend_schema(
        tags=["Dealers - Sales"],
        description="Create a lead (brokers for their cars, dealers for their cars, admins).",
        request=LeadSerializer,
        responses={
            201: LeadSerializer,
            400: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="Invalid input.",
                examples=[OpenApiExample("Invalid input", value={"detail": "Invalid data."})]
            ),
            403: OpenApiResponse(
                response={"type": "object", "properties": {"detail": {"type": "string"}}},
                description="User lacks permission.",
                examples=[OpenApiExample("Forbidden", value={"detail": "Only brokers, dealers, or admins can create leads."})]
            )
        }
    ),
    update=extend_schema(
        tags=["Dealers - Sales"],
        description="Update a lead (brokers for their cars, dealers for their cars, admins).",
        request=LeadSerializer,
        responses={200: LeadSerializer}
    ),
    partial_update=extend_schema(
        tags=["Dealers - Sales"],
        description="Partially update a lead.",
        request=LeadSerializer,
        responses={200: LeadSerializer}
    ),
    destroy=extend_schema(
        tags=["Dealers - Sales"],
        description="Delete a lead (brokers for their cars, dealers for their cars, admins).",
        responses={204: None}
    ),
)
class LeadViewSet(ModelViewSet):
    queryset = Lead.objects.all()
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), has_manage_sales_permission]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset
        elif has_role(user, 'broker'):
            try:
                broker_profile = BrokerProfile.objects.get(profile__user=user)
                return self.queryset.filter(car__broker=broker_profile)
            except BrokerProfile.DoesNotExist:
                return self.queryset.none()
        elif has_role(user, 'dealer'):
            try:
                dealer_profile = DealerProfile.objects.get(profile__user=user)
                return self.queryset.filter(car__dealer=dealer_profile)
            except DealerProfile.DoesNotExist:
                return self.queryset.none()
        return self.queryset.none()
