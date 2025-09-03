from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, extend_schema_view
from .serializers import UpgradeToDealerSerializer, UpgradeToBrokerSerializer
import logging

logger = logging.getLogger(__name__)

@extend_schema_view(
    upgrade_to_dealer=extend_schema(
        tags=["buyers"],
        request=UpgradeToDealerSerializer,
        responses={201: UpgradeToDealerSerializer},
        description="Request to upgrade authenticated user to dealer role."
    ),
    upgrade_to_broker=extend_schema(
        tags=["buyers"],
        request=UpgradeToBrokerSerializer,
        responses={201: UpgradeToBrokerSerializer},
        description="Request to upgrade authenticated user to broker role."
    )
)
class RoleUpgradeViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def upgrade_to_dealer(self, request):
        serializer = UpgradeToDealerSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        dealer = serializer.save()
        logger.info(f"User {request.user.email} upgraded to dealer with profile ID {dealer.pk}")
        return Response(serializer.data, status=201)

    @action(detail=False, methods=['post'])
    def upgrade_to_broker(self, request):
        serializer = UpgradeToBrokerSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        broker = serializer.save()
        logger.info(f"User {request.user.email} upgraded to broker with profile ID {broker.pk}")
        return Response(serializer.data, status=201)
