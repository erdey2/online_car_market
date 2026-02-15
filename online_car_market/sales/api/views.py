from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rolepermissions.checkers import has_role
from online_car_market.sales.models import Sale, Lead
from online_car_market.dealers.models import DealerStaff
from .serializers import SaleSerializer, LeadSerializer, LeadCreateSerializer, LeadStatusUpdateSerializer
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
        summary="List Leads",
        description=(
            "Returns leads based on user role:\n"
            "- Admin → All leads\n"
            "- Dealer/Broker/Seller → Leads for their cars\n"
            "- Buyer → Their own leads"
        ),
        responses=LeadSerializer(many=True),
    ),
    retrieve=extend_schema(
        tags=["Dealers - Sales"],
        summary="Retrieve Lead",
        description="Retrieve detailed information about a specific lead.",
        responses=LeadSerializer,
    ),
    create=extend_schema(
        tags=["Dealers - Sales"],
        summary="Create Lead (Buyer Inquiry)",
        description="Creates a new lead for a specific car.",
        request=LeadCreateSerializer,
        responses={201: LeadSerializer},
        examples=[
            OpenApiExample(
                "Create Lead Example",
                value={
                    "car_id": 15,
                    "name": "John Doe",
                    "contact": "john@email.com"
                },
                request_only=True,
            )
        ],
    ),
)
class LeadViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    queryset = Lead.objects.select_related("car", "buyer")
    serializer_class = LeadSerializer

    def get_serializer_class(self):
        if self.action == "create":
            return LeadCreateSerializer
        if self.action == "update_status":
            return LeadStatusUpdateSerializer
        return LeadSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return self.queryset

        if hasattr(user, "dealer"):
            return self.queryset.filter(car__dealer=user.dealer)

        if hasattr(user, "broker"):
            return self.queryset.filter(car__broker=user.broker)

        return self.queryset.filter(buyer=user)

    @extend_schema(
        tags=["Dealers - Sales"],
        summary="Update Lead Status",
        description=(
            "Updates the status of a lead.\n\n"
            "Only sellers (dealer/broker) or admin can update status.\n\n"
            "When status is changed to CLOSED:\n"
            "- Lead is marked as closed\n"
            "- Car is automatically marked as sold"
        ),
        request=LeadStatusUpdateSerializer,
        responses={200: LeadSerializer},
        examples=[
            OpenApiExample(
                "Update Status Example",
                value={"status": "closed"},
                request_only=True,
            )
        ],
    )
    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsAuthenticated],
    )
    def update_status(self, request, pk=None):
        lead = self.get_object()

        serializer = self.get_serializer(
            lead,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            LeadSerializer(lead).data,
            status=status.HTTP_200_OK,
        )




