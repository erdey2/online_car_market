from rest_framework.permissions import IsAuthenticated

from .serializers import InspectionSerializer, InspectorSerializer, CreateInspectorSerializer
from ..models import Inspection, Inspector
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, OpenApiExample
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.decorators import action
from online_car_market.users.permissions.business_permissions import IsAdminOrReadOnly
from online_car_market.users.permissions.drf_permissions import IsInspector, IsSuperAdminOrAdmin
from ..services.inspection_service import InspectionService, InspectorService


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
                    "inspector_id": 3,
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
    queryset = Inspection.objects.select_related(
        "car",
        "inspector",
        "uploaded_by",
        "verified_by"
    )
    serializer_class = InspectionSerializer

    def get_permissions(self):
        if self.action == "verify":
            return [IsSuperAdminOrAdmin()]

        if self.action in ["create", "update", "partial_update"]:
            return [IsInspector()]

        elif self.action == "destroy":
            return [permissions.IsAdminUser()]

        return [IsAdminOrReadOnly()]

    def get_queryset(self):

        user = self.request.user

        if user.role in [
            "admin",
            "super_admin"
        ]:
            return Inspection.objects.all()

        if hasattr(user, "inspector_profile"):
            return Inspection.objects.filter(
                inspector=user.inspector_profile
            )

        return Inspection.objects.filter(
            status="verified"
        )

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

        if inspection.status == "verified":
            return Response(
                {"detail": "Inspection already verified."},
                status=400
            )

        InspectionService.verify_inspection(
            inspection=inspection,
            user=request.user,
            status_value=request.data.get("status"),
            admin_remarks=request.data.get("admin_remarks", "")
        )

        return Response({"detail": "Inspection updated successfully."})


@extend_schema_view(
    list=extend_schema(
        tags=["Inspectors"],
        summary="List inspectors",
        description=(
            "Retrieve all registered inspectors. "
            "Only administrators and super administrators can access this endpoint."
        ),
        responses={200: InspectorSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Inspectors"],
        summary="Retrieve inspector details",
        description="Retrieve detailed information about a specific inspector.",
        responses={200: InspectorSerializer},
    ),
    create=extend_schema(
        tags=["Inspectors"],
        summary="Register a new inspector",
        description=(
            "Create a new inspector account and assign the inspector role. "
            "Only administrators and super administrators can perform this action."
        ),
        request=CreateInspectorSerializer,
        examples=[
            OpenApiExample(
                "Create Inspector",
                value={
                    "email": "inspector@example.com",
                    "first_name": "Abebe",
                    "last_name": "Kebede",
                    "company_name": "AA Vehicle Inspection Center",
                    "license_number": "LIC-12345",
                    "password": "StrongPassword123"
                },
            )
        ],
        responses={
            201: OpenApiResponse(
                response=InspectorSerializer,
                description="Inspector created successfully."
            ),
            400: OpenApiResponse(
                description="Validation error."
            ),
            403: OpenApiResponse(
                description="Permission denied."
            ),
        },
    ),
    update=extend_schema(
        tags=["Inspectors"],
        summary="Update inspector",
        description="Update an inspector profile.",
        responses={
            200: InspectorSerializer,
            403: OpenApiResponse(description="Permission denied."),
        },
    ),
    partial_update=extend_schema(
        tags=["Inspectors"],
        summary="Partially update inspector",
        description="Partially update inspector information.",
        responses={
            200: InspectorSerializer,
            403: OpenApiResponse(description="Permission denied."),
        },
    ),
    destroy=extend_schema(
        tags=["Inspectors"],
        summary="Delete inspector",
        description=(
            "Delete an inspector account. "
            "Use with caution because inspection history may depend on this record."
        ),
        responses={
            204: OpenApiResponse(
                description="Inspector deleted successfully."
            ),
            403: OpenApiResponse(
                description="Permission denied."
            ),
        },
    ),
)
class InspectorViewSet(ModelViewSet):

    queryset = Inspector.objects.select_related(
        "user",
        "created_by"
    )

    permission_classes = [IsAuthenticated, IsSuperAdminOrAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateInspectorSerializer

        return InspectorSerializer

    def perform_create(self, serializer):

        InspectorService.create_inspector(
            admin_user=self.request.user,
            validated_data=serializer.validated_data
        )


