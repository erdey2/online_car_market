from .serializers import InspectionSerializer
from ..models import Inspection
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, OpenApiExample
from rest_framework.viewsets import ModelViewSet
from online_car_market.users.permissions.drf_permissions import IsBrokerOrSeller, IsSuperAdminOrAdmin
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.decorators import action
from rolepermissions.checkers import has_role
from online_car_market.users.permissions.business_permissions import IsAdminOrReadOnly
from online_car_market.inspection.services.inspection_service import InspectionService


@extend_schema_view(
    list=extend_schema(
        tags=["Car Inspections"],
        summary="List all inspections",
        description="Retrieve a list of all inspections. Admins see all, while brokers/sellers see their own.",
        responses={200: InspectionSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Car Inspections"],
        summary="Retrieve a specific inspection",
        description="Get detailed information about a specific inspection record.",
        responses={200: InspectionSerializer},
    ),
    create=extend_schema(
        tags=["Car Inspections"],
        summary="Create a new inspection",
        description="Allows a broker or seller to create a new inspection for a car.",
        request=InspectionSerializer,
        examples=[
            OpenApiExample(
                "Example Request",
                value={
                    "car_id": 12,
                    "inspected_by": "Top Garage Motors",
                    "inspection_date": "2025-11-10",
                    "remarks": "Engine and brakes are in excellent condition.",
                    "condition_status": "excellent"
                },
            ),
        ],
        responses={
            201: OpenApiResponse(response=InspectionSerializer, description="Inspection created successfully"),
            403: OpenApiResponse(description="Permission denied"),
        },
    ),
    update=extend_schema(
        tags=["Car Inspections"],
        summary="Update an inspection",
        description="Allows brokers or sellers to update an existing inspection they created.",
        responses={
            200: InspectionSerializer,
            403: OpenApiResponse(description="Permission denied"),
        },
    ),
    partial_update=extend_schema(
        tags=["Car Inspections"],
        summary="Partially update an inspection",
        description="Allows brokers or sellers to partially update fields of an existing inspection.",
    ),
    destroy=extend_schema(
        tags=["Car Inspections"],
        summary="Delete an inspection",
        description="Allows only admins to delete an inspection.",
        responses={204: OpenApiResponse(description="Deleted successfully")},
    ),
)
class InspectionViewSet(ModelViewSet):
    queryset = Inspection.objects.select_related("car", "uploaded_by", "verified_by")
    serializer_class = InspectionSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update"]:
            return [IsBrokerOrSeller()]
        elif self.action in ["verify", "destroy"]:
            return [permissions.IsAdminUser()]
        else:
            return [IsAdminOrReadOnly()]

    def get_queryset(self):
        user = self.request.user

        if has_role(user, ["admin", "superadmin"]):
            return Inspection.objects.all()
        return Inspection.objects.filter(uploaded_by=user)

    @extend_schema(
        description="Verify or reject an inspection."
                    "This endpoint allows an **admin or superadmin** to update the inspection status "
                    "to either `'verified'` or `'rejected'`. Optionally, an admin can include remarks.",
        parameters=[
            OpenApiParameter(
                name="status",
                type=str,
                required=True,
                description="The new status. Must be either 'verified' or 'rejected'."
            ),
            OpenApiParameter(
                name="admin_remarks",
                type=str,
                required=False,
                description="Optional remarks from the admin."
            ),
        ],
        responses={
            200: OpenApiResponse(description="Inspection verified or rejected successfully."),
            400: OpenApiResponse(description="Invalid status or bad request."),
            403: OpenApiResponse(description="Forbidden – user not authorized."),
            404: OpenApiResponse(description="Inspection not found."),
        },
    )
    @extend_schema(
        tags=["Car Inspections"],
        summary="Verify or reject an inspection.",
        description=(
            "Verify or reject a car inspection.\n\n"
            "**Admin-only action** that updates the inspection status and records "
            "who verified it and when."
        ),
        request=InspectionSerializer,
        responses={
            200: OpenApiResponse(
                description="Inspection verified or rejected successfully.",
                examples=[
                    OpenApiExample(
                        "Verified",
                        value={"detail": "Inspection verified successfully."}
                    ),
                    OpenApiExample(
                        "Rejected",
                        value={"detail": "Inspection rejected successfully."}
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Invalid status value.",
                examples=[
                    OpenApiExample(
                        "Invalid Status",
                        value={"error": "Invalid status. Must be 'verified' or 'rejected'."}
                    )
                ],
            ),
            403: OpenApiResponse(
                description="User does not have permission to verify inspections.",
                examples=[
                    OpenApiExample(
                        "Forbidden",
                        value={"detail": "You do not have permission to perform this action."}
                    )
                ],
            ),
            404: OpenApiResponse(
                description="Inspection not found."
            ),
        },
    )
    @action(detail=True, methods=["patch"], permission_classes=[IsSuperAdminOrAdmin])
    def verify(self, request, pk=None):
        inspection = self.get_object()

        InspectionService.verify_inspection(
            inspection=inspection,
            user=request.user,
            status_value=request.data.get("status"),
            admin_remarks=request.data.get("admin_remarks", "")
        )

        return Response({"detail": "Inspection updated successfully."})


