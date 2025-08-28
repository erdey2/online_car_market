from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rolepermissions.checkers import has_role
from online_car_market.users.permissions import IsSuperAdminOrAdminOrBuyer
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes
from ..models import Dealer, DealerRating
from .serializers import DealerSerializer, UpgradeToDealerSerializer, VerifyDealerSerializer, DealerRatingSerializer


@extend_schema_view(
    list=extend_schema(tags=["Dealers - Profiles"], description="List all dealers (admin only)."),
    retrieve=extend_schema(tags=["Dealers - Profiles"], description="Retrieve a dealer profile."),
    create=extend_schema(tags=["Dealers - Profiles"], description="Create a dealer profile (admin only)."),
    update=extend_schema(tags=["Dealers - Profiles"], description="Update a dealer profile (admin or owner)."),
    partial_update=extend_schema(tags=["Dealers - Profiles"], description="Partially update a dealer profile."),
    destroy=extend_schema(tags=["Dealers - Profiles"], description="Delete a dealer profile (admin only)."),
)
@extend_schema(parameters=[OpenApiParameter(name="id", type=OpenApiTypes.INT, location="path", description="Dealer ID")])
class DealerProfileViewSet(ModelViewSet):
    serializer_class = DealerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return Dealer.objects.all()
        return Dealer.objects.filter(user=user)

    @extend_schema(
        tags=["Dealers - Profiles"],
        description="Verify a dealer profile (admin/super_admin only).",
        responses=VerifyDealerSerializer
    )
    @action(detail=True, methods=['patch'], serializer_class=VerifyDealerSerializer)
    def verify(self, request, pk=None):
        dealer = self.get_object()
        serializer = self.get_serializer(dealer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Dealers - Profiles"],
        description="Request to upgrade to dealer role.",
        responses=DealerSerializer
    )
    @action(detail=False, methods=['post'], serializer_class=UpgradeToDealerSerializer)
    def upgrade(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        dealer = serializer.save()
        return Response(DealerSerializer(dealer).data)

@extend_schema_view(
    list=extend_schema(tags=["Dealers - Ratings"], description="List all ratings for a dealer."),
    retrieve=extend_schema(tags=["Dealers - Ratings"], description="Retrieve a specific dealer rating."),
    create=extend_schema(tags=["Dealers - Ratings"], description="Create a dealer rating (authenticated users only)."),
    update=extend_schema(tags=["Dealers - Ratings"], description="Update a dealer rating (rating owner or admin only)."),
    partial_update=extend_schema(tags=["Dealers - Ratings"], description="Partially update a dealer rating."),
    destroy=extend_schema(tags=["Dealers - Ratings"], description="Delete a dealer rating (rating owner or admin only)."),
)
class DealerRatingViewSet(ModelViewSet):
    serializer_class = DealerRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        dealer_id = self.kwargs.get('dealer_id')
        user = self.request.user
        if has_role(user, ['super_admin', 'admin']):
            return DealerRating.objects.filter(dealer_id=dealer_id)
        return DealerRating.objects.filter(dealer_id=dealer_id, user=user)

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            return [IsAuthenticated()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSuperAdminOrAdminOrBuyer()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        dealer_id = self.kwargs.get('dealer_id')
        dealer = Dealer.objects.get(id=dealer_id)
        serializer.save(dealer=dealer, user=self.request.user)
