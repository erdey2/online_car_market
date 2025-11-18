from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..models import Bid
from .serializers import BidSerializer
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from online_car_market.users.permissions.drf_permissions import IsBuyer, IsSuperAdminOrAdmin


@extend_schema_view(
    list=extend_schema(
        tags=["Bids"],
        summary="List Bids",
        description="List all bids made by the authenticated user (Buyers only).",
        responses={200: BidSerializer(many=True)},
    ),
    create=extend_schema(
        tags=["Bids"],
        summary="Create a New Bid",
        description="Create a new bid on a car. Only users with the 'buyer' role can perform this action.",
        request=BidSerializer,
        responses={201: BidSerializer},
    ),
    retrieve=extend_schema(
        tags=["Bids"],
        summary="Retrieve a Bid",
        description="Retrieve a specific bid by its ID. Only the bid owner (Buyer) can access it.",
        responses={200: BidSerializer},
    ),
    update=extend_schema(
        tags=["Bids"],
        summary="Update a Bid",
        description="Fully update a bid (e.g., change car or amount). Only the bid owner (Buyer) can perform this action.",
        request=BidSerializer,
        responses={200: BidSerializer},
    ),
    partial_update=extend_schema(
        tags=["Bids"],
        summary="Partially Update a Bid",
        description="Partially update a bid (e.g., modify amount). Only the bid owner (Buyer) can do this.",
        request=BidSerializer,
        responses={200: BidSerializer},
    ),
    destroy=extend_schema(
        tags=["Bids"],
        summary="Delete a Bid",
        description="Delete a bid. Only the bid owner (Buyer) can delete their own bid.",
        responses={204: None},
    ),
)
class BidViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BidSerializer
    queryset = Bid.objects.all()

    def get_queryset(self):
        user = self.request.user
        if has_role(user, ["admin", "superadmin"]):
            return Bid.objects.all()
        return Bid.objects.filter(user=user)

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "list", "retrieve"]:
            return [IsAuthenticated(), IsBuyer()]
        elif self.action in ["manage"]:
            return [IsAuthenticated(), IsSuperAdminOrAdmin()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response({"detail": "User does not have buyer role."}, status=status.HTTP_403_FORBIDDEN)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response({"detail": "User does not have buyer role."}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response({"detail": "User does not have buyer role."}, status=status.HTTP_403_FORBIDDEN)
        try:
            bid = self.get_queryset().get(pk=kwargs['pk'])
            serializer = self.get_serializer(bid)
            return Response(serializer.data)
        except Bid.DoesNotExist:
            return Response({"detail": "Bid not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response({"detail": "User does not have buyer role."}, status=status.HTTP_403_FORBIDDEN)
        try:
            bid = self.get_queryset().get(pk=kwargs['pk'])
            serializer = self.get_serializer(bid, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Bid.DoesNotExist:
            return Response({"detail": "Bid not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

    def partial_update(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response({"detail": "User does not have buyer role."}, status=status.HTTP_403_FORBIDDEN)
        try:
            bid = self.get_queryset().get(pk=kwargs['pk'])
            serializer = self.get_serializer(bid, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Bid.DoesNotExist:
            return Response({"detail": "Bid not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response({"detail": "User does not have buyer role."}, status=status.HTTP_403_FORBIDDEN)
        try:
            bid = self.get_queryset().get(pk=kwargs['pk'])
            bid.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Bid.DoesNotExist:
            return Response({"detail": "Bid not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        tags=["Bids"],
        summary="Approve or Reject a Bid",
        description="Admins or SuperAdmins can approve or reject a bid. "
                    "Expected body: `{ 'status': 'approved' }` or `{ 'status': 'rejected' }`.",
        request={
            "application/json": {
                "type": "object",
                "properties": {"status": {"type": "string", "enum": ["approved", "rejected"]}},
                "required": ["status"],
            }
        },
        responses={200: {"description": "Bid successfully updated"}},
    )
    @action(detail=True, methods=["patch"], permission_classes=[IsSuperAdminOrAdmin])
    def manage(self, request, pk=None):
        bid = self.get_object()
        status_value = request.data.get("status")
        if status_value not in ["approved", "rejected"]:
            return Response({"error": "Invalid status. Must be 'approved' or 'rejected'."}, status=status.HTTP_400_BAD_REQUEST)
        bid.status = status_value
        bid.save()
        return Response({"detail": f"Bid {status_value} successfully."}, status=status.HTTP_200_OK)


