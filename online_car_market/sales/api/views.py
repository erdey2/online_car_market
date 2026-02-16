from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.permissions import IsAuthenticated
from online_car_market.sales.models import Lead
from .serializers import SaleSerializer, LeadSerializer, LeadCreateSerializer, LeadStatusUpdateSerializer, LeadAnalyticsSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse, OpenApiExample
from online_car_market.users.permissions.business_permissions import CanViewSalesData, CanManageSales
from ..service.lead_service import LeadService
from ..service.sale_service import SaleService

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
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated & CanViewSalesData]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageSales()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return SaleService.get_sales_for_user(self.request.user)


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
                    "name": "Abebe Alemu",
                    "contact": "abebe@email.com"
                },
                request_only=True,
            )
        ],
    ),
    update_status=extend_schema(
        tags=["Dealers - Sales"],
        summary="Update Lead Status",
        description=(
        "Updates the status of a specific lead.\n\n"
        "Allowed statuses:\n"
        "- inquiry\n"
        "- contacted\n"
        "- negotiation\n"
        "- closed\n"
        "- lost\n"
        "- cancelled\n\n"
    ),
        request=LeadStatusUpdateSerializer,
        responses={200: LeadSerializer},
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

    @action(detail=True, methods=["patch"], permission_classes=[IsAuthenticated])
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

    @extend_schema(
        tags=["Dealers - Sales"],
        summary="Leads Analytics",
        description=(
            "Returns analytics about leads:\n"
            "- Total leads\n"
            "- Leads per status\n"
            "- Conversion rate\n"
            "- Average time to close"
        ),
        responses=LeadAnalyticsSerializer,
    )
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def analytics(self, request):
        user = request.user
        data = {
            "total_leads": LeadService.total_leads(user),
            "conversion_rate": LeadService.conversion_rate(user),
            "leads_by_status": LeadService.leads_by_status(user),
            "avg_time_to_close": LeadService.avg_time_to_close(user),
        }
        return Response(data)




