from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from ..models import Buyer, Rating, LoyaltyProgram
from .serializers import BuyerSerializer, RatingSerializer, LoyaltyProgramSerializer
from online_car_market.users.api.views import IsAdmin

class BuyerViewSet(ModelViewSet):
    queryset = Buyer.objects.all()
    serializer_class = BuyerSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

class RatingViewSet(ModelViewSet):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.userprofile.role == 'buyer':
            return Rating.objects.filter(buyer=self.request.user)
        return Rating.objects.all()

class LoyaltyProgramViewSet(ModelViewSet):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.userprofile.role == 'buyer':
            return LoyaltyProgram.objects.filter(buyer__user=self.request.user)
        return LoyaltyProgram.objects.all()
