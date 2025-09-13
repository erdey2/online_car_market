from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from ..models import Bid
from .serializers import BidSerializer
from rolepermissions.checkers import has_role
from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

class BidViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BidSerializer
    queryset = Bid.objects.all()

    def get_queryset(self):
        # Restrict to bids by the authenticated user
        return self.queryset.filter(user=self.request.user)

    @extend_schema(
        tags=["Bids"],
        description="List all bids made by the authenticated user.",
        responses={200: BidSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["Bids"],
        description="Create a new bid on a car. User must have buyer role.",
        request=BidSerializer,
        responses={201: BidSerializer}
    )
    def create(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=["Bids"],
        description="Retrieve a specific bid. User must be the bid owner.",
        responses={200: BidSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            bid = self.get_queryset().get(pk=kwargs['pk'])
            serializer = self.get_serializer(bid)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Bid.DoesNotExist:
            return Response(
                {"detail": "Bid not found or you do not have permission to view it."},
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        tags=["Bids"],
        description="Fully update a bid (e.g., car and amount). User must be the bid owner.",
        request=BidSerializer,
        responses={200: BidSerializer}
    )
    def update(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            bid = self.get_queryset().get(pk=kwargs['pk'])
            serializer = self.get_serializer(bid, data=request.data, partial=False)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Bid.DoesNotExist:
            return Response(
                {"detail": "Bid not found or you do not have permission to update it."},
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        tags=["Bids"],
        description="Partially update a bid's amount. User must be the bid owner.",
        request=BidSerializer,
        responses={200: BidSerializer}
    )
    def partial_update(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            bid = self.get_queryset().get(pk=kwargs['pk'])
            serializer = self.get_serializer(bid, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Bid.DoesNotExist:
            return Response(
                {"detail": "Bid not found or you do not have permission to update it."},
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        tags=["Bids"],
        description="Delete a bid. User must be the bid owner.",
        responses={204: None}
    )
    def destroy(self, request, *args, **kwargs):
        if not has_role(request.user, 'buyer'):
            return Response(
                {"detail": "User does not have buyer role."},
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            bid = self.get_queryset().get(pk=kwargs['pk'])
            bid.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Bid.DoesNotExist:
            return Response(
                {"detail": "Bid not found or you do not have permission to delete it."},
                status=status.HTTP_404_NOT_FOUND
            )
