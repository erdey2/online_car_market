from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from ..models import Buyer, Rating, LoyaltyProgram, Dealer
from .serializers import BuyerSerializer, RatingSerializer, LoyaltyProgramSerializer, DealerSerializer
from online_car_market.users.api.views import IsAdmin
from drf_spectacular.utils import extend_schema, extend_schema_view

@extend_schema_view(
    list=extend_schema(tags=["buyers"]),
    retrieve=extend_schema(tags=["buyers"]),
    create=extend_schema(tags=["buyers"]),
    update=extend_schema(tags=["buyers"]),
    destroy=extend_schema(tags=["buyers"]),
)
class BuyerViewSet(ModelViewSet):
    queryset = Buyer.objects.all()
    serializer_class = BuyerSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

@extend_schema_view(
    list=extend_schema(tags=["dealer"]),
    retrieve=extend_schema(tags=["dealer"]),
    create=extend_schema(tags=["dealer"]),
    update=extend_schema(tags=["dealer"]),
    destroy=extend_schema(tags=["dealer"]),
)
class DealerProfileViewSet(ModelViewSet):
    queryset = Dealer.objects.all()
    serializer_class = DealerSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

@extend_schema_view(
    list=extend_schema(tags=["buyers"]),
    retrieve=extend_schema(tags=["buyers"]),
    create=extend_schema(tags=["buyers"]),
    update=extend_schema(tags=["buyers"]),
    destroy=extend_schema(tags=["buyers"]),
)
class RatingViewSet(ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.userprofile.role == 'buyer':
            return Rating.objects.filter(buyer=self.request.user)
        return Rating.objects.all()

@extend_schema_view(
    list=extend_schema(tags=["buyers"]),
    retrieve=extend_schema(tags=["buyers"]),
    create=extend_schema(tags=["buyers"]),
    update=extend_schema(tags=["buyers"]),
    destroy=extend_schema(tags=["buyers"]),
)
class LoyaltyProgramViewSet(ModelViewSet):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.userprofile.role == 'buyer':
            return LoyaltyProgram.objects.filter(buyer__user=self.request.user)
        return LoyaltyProgram.objects.all()
