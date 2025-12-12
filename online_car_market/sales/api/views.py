from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rolepermissions.checkers import has_role
from online_car_market.sales.models import Sale, Lead
from online_car_market.dealers.models import DealerStaff
from .serializers import SaleSerializer, LeadSerializer
from online_car_market.brokers.models import BrokerProfile
from online_car_market.dealers.models import DealerProfile
from online_car_market.buyers.models import BuyerProfile
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample
from online_car_market.users.permissions.business_permissions import CanViewSalesData, CanManageSales

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
    permission_classes = [IsAuthenticated & CanViewSalesData]

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
        description="List leads based on user role: brokers/dealers see leads for their cars, sellers see leads for their dealer, admins see all.",
        responses={
            200: LeadSerializer(many=True),
            403: OpenApiResponse(
                description="User lacks permission.",
                examples=[OpenApiExample("Forbidden", value={"detail": "You do not have permission."})]
            )
        }
    ),
    retrieve=extend_schema(
        tags=["Dealers - Sales"],
        description="Retrieve a specific lead if the user has permission.",
        responses={
            200: LeadSerializer,
            404: OpenApiResponse(
                description="Lead not found.",
                examples=[OpenApiExample("Not Found", value={"detail": "Not found."})]
            ),
            403: OpenApiResponse(
                description="Forbidden.",
                examples=[OpenApiExample("Forbidden", value={"detail": "You do not have permission."})]
            )
        }
    ),
    create=extend_schema(
        tags=["Dealers - Sales"],
        description="Create a lead. Allowed for brokers, dealers, sellers, and admins.",
        request=LeadSerializer,
        responses={
            201: LeadSerializer,
            400: OpenApiResponse(
                description="Invalid input.",
                examples=[OpenApiExample("Invalid input", value={"detail": "Invalid data."})]
            ),
            403: OpenApiResponse(
                description="Forbidden.",
                examples=[OpenApiExample("Forbidden", value={"detail": "Permission denied."})]
            )
        }
    ),
    update=extend_schema(
        tags=["Dealers - Sales"],
        description="Update a lead.",
        request=LeadSerializer,
        responses={
            200: LeadSerializer,
            403: OpenApiResponse(description="Forbidden.")
        }
    ),
    partial_update=extend_schema(
        tags=["Dealers - Sales"],
        description="Partially update a lead.",
        request=LeadSerializer,
        responses={
            200: LeadSerializer,
            403: OpenApiResponse(description="Forbidden.")
        }
    ),
    destroy=extend_schema(
        tags=["Dealers - Sales"],
        description="Delete a lead.",
        responses={
            204: None,
            403: OpenApiResponse(description="Forbidden.")
        }
    ),
)
class LeadViewSet(ModelViewSet):
    queryset = Lead.objects.all().order_by('-created_at')
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # Only write operations require CanManageSales
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageSales()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        # Admins see everything
        if has_role(user, ['super_admin', 'admin']):
            return self.queryset

        # Broker: cars assigned to this broker
        if has_role(user, 'broker'):
            broker = BrokerProfile.objects.filter(profile__user=user).first()
            if broker:
                return self.queryset.filter(car__broker=broker)
            return self.queryset.none()

        # Dealer: all cars of dealer
        if has_role(user, 'dealer'):
            dealer = DealerProfile.objects.filter(profile__user=user).first()
            if dealer:
                return self.queryset.filter(car__dealer=dealer)
            return self.queryset.none()

        # Seller: leads for cars of their dealer
        if has_role(user, 'seller'):
            staff = DealerStaff.objects.filter(user=user).first()
            if staff:
                return self.queryset.filter(car__dealer=staff.dealer)
            return self.queryset.none()

        # Buyer: their own leads
        if has_role(user, 'buyer'):
            buyer = BuyerProfile.objects.filter(profile__user=user).first()
            if buyer:
                return self.queryset.filter(buyer=user)
            return self.queryset.none()

        return self.queryset.none()
