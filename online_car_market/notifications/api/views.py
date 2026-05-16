from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
    OpenApiResponse,
    OpenApiExample,
    inline_serializer,
)
from rest_framework import serializers
from ..models import Notification, Device, NotificationPreference
from .serializers import NotificationSerializer, DeviceSerializer, NotificationPreferenceSerializer

@extend_schema_view(
    list=extend_schema(
        summary="List my notifications",
        description=(
            "Return notifications for the authenticated user, ordered from newest to oldest. "
            "Use `unread=true` to return only unread items."
        ),
        parameters=[
            OpenApiParameter(
                name="unread",
                description="Filter to unread notifications only.",
                required=False,
                type=OpenApiTypes.BOOL,
            )
        ],
        responses={200: NotificationSerializer(many=True)},
    ),
    mark_read=extend_schema(
        summary="Mark one notification or all notifications as read",
        description=(
            "If `id` is provided, mark that single notification as read. "
            "If `id` is omitted, mark all unread notifications for the current user as read."
        ),
        request=inline_serializer(
            name="MarkNotificationReadRequest",
            fields={
                "id": serializers.IntegerField(required=False),
            },
        ),
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="MarkNotificationReadResponse",
                    fields={
                        "status": serializers.CharField(),
                    },
                ),
                examples=[OpenApiExample("Success", value={"status": "ok"})],
            ),
            404: OpenApiResponse(description="Notification not found for the current user."),
        },
    ),
    unread_count=extend_schema(
        summary="Get unread notification count",
        description="Return the number of unread notifications for the authenticated user.",
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="UnreadNotificationCountResponse",
                    fields={
                        "unread": serializers.IntegerField(),
                    },
                ),
                examples=[OpenApiExample("Unread count", value={"unread": 3})],
            )
        },
    ),
)
class NotificationViewSet(ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user).order_by("-created_at")
        if self.request.query_params.get("unread") == "true":
            qs = qs.filter(is_read=False)

        return qs

    @action(detail=False, methods=["post"])
    def mark_read(self, request):
        notification_id = request.data.get("id")
        user = request.user

        if notification_id:
            n = get_object_or_404(Notification, id=notification_id, recipient=user)
            n.is_read = True
            n.save()
        else:
            Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)

        return Response({"status": "ok"})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread": count})

@extend_schema(
    tags=["Notifications - Devices"],
    description="Manage the authenticated user's registered FCM push devices.",
)
@extend_schema_view(
    list=extend_schema(
        summary="List my registered devices",
        description="Return all push notification devices registered by the authenticated user.",
        responses={200: DeviceSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Retrieve a registered device",
        description="Return details for one of the authenticated user's registered devices.",
        responses={200: DeviceSerializer, 404: OpenApiResponse(description="Device not found." )},
    ),
    create=extend_schema(
        summary="Register or update a device",
        description=(
            "Register a device token for FCM push notifications. "
            "If the token already exists, the device is updated for the current user."
        ),
        request=DeviceSerializer,
        responses={201: DeviceSerializer},
    ),
    destroy=extend_schema(
        summary="Delete a registered device",
        description="Remove a registered push notification device from the authenticated user's account.",
        responses={204: None},
    ),
)
class DeviceViewSet(ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Device.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        token = serializer.validated_data["fcm_token"]

        device, _ = Device.objects.update_or_create(
            fcm_token=token,
            defaults={
                "user": self.request.user,
                "platform": serializer.validated_data["platform"]
            }
        )
        serializer.instance = device

class NotificationPreferenceView(RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj
