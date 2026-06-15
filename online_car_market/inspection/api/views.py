from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .serializers import InspectionSerializer, InspectorSerializer, CreateInspectorSerializer, InspectionVerificationSerializer
from ..models import Inspection, Inspector
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, OpenApiExample
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.decorators import action
from online_car_market.users.permissions.drf_permissions import IsInspector, IsSuperAdminOrAdmin
from ..services.inspection_service import InspectionService, InspectorService


@extend_schema_view(
    list=extend_schema(
        tags=["Car Inspections"],
        summary="List inspections",
        description="""
Retrieve inspections based on the authenticated user's role:

- Admin / Super Admin → all inspections
- Inspector → their assigned inspections
- Dealer / Broker → inspections related to their cars
- Public users → verified inspections only
""",
        responses={200: InspectionSerializer(many=True)},
    ),

    retrieve=extend_schema(
        tags=["Car Inspections"],
        summary="Retrieve inspection details",
        description="Retrieve a single inspection record by ID.",
        responses={200: InspectionSerializer},
    ),

    create=extend_schema(
        tags=["Car Inspections"],
        summary="Create inspection",
        description="""
Create a new inspection record.

Only users with the Inspector role can perform this action.
""",
        request=InspectionSerializer,
        examples=[
            OpenApiExample(
                "Inspection Creation Example",
                value={
                    "car_id": 12,
                    "inspection_date": "2026-06-14",
                    "inspection_score": 92,
                    "odometer_verified": True,
                    "accident_history": False,
                    "condition_status": "good",
                    "remarks": "Vehicle passed inspection.",
                    "signed_report": "<uploaded_file>"
                },
            )
        ],
        responses={
            201: InspectionSerializer,
            400: OpenApiResponse(description="Validation error."),
            403: OpenApiResponse(description="Only inspectors can create inspections."),
        },
    ),

    update=extend_schema(
        tags=["Car Inspections"],
        summary="Update inspection",
        description="""
Update an existing inspection.

Rules:
- Only the assigned inspector can update
- Only pending inspections can be modified
""",
        responses={
            200: InspectionSerializer,
            403: OpenApiResponse(description="Permission denied."),
        },
    ),

    partial_update=extend_schema(
        tags=["Car Inspections"],
        summary="Partially update inspection",
        description="""
Partially update a pending inspection.

Only the assigned inspector can perform this action.
""",
        responses={
            200: InspectionSerializer,
            403: OpenApiResponse(description="Permission denied."),
        },
    ),

    destroy=extend_schema(
        tags=["Car Inspections"],
        summary="Delete inspection",
        description="""
Delete an inspection record.

Only Admin and Super Admin can delete inspections.
""",
        responses={
            204: OpenApiResponse(description="Inspection deleted successfully."),
            403: OpenApiResponse(description="Permission denied."),
        },
    ),
)
class InspectionViewSet(ModelViewSet):

    serializer_class = InspectionSerializer

    def get_permissions(self):

        if self.action == "verify":
            return [IsSuperAdminOrAdmin()]

        if self.action in ["create"]:
            return [IsInspector()]

        if self.action in ["update", "partial_update"]:
            return [IsInspector()]

        if self.action == "destroy":
            return [IsSuperAdminOrAdmin()]

        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return InspectionService.get_user_inspections(
            self.request.user
        )

    @extend_schema(
        tags=["Car Inspections"],
        summary="Verify or reject inspection",
        description="""
Admin-only endpoint to verify or reject an inspection.

Allowed status values:
- verified
- rejected

This action also records:
- verifier
- verification timestamp
- admin remarks
""",
        request=InspectionVerificationSerializer,
        responses={
            200: OpenApiResponse(description="Inspection updated successfully."),
            400: OpenApiResponse(description="Invalid status value."),
            403: OpenApiResponse(description="Only admins can verify inspections."),
            404: OpenApiResponse(description="Inspection not found."),
        },
    )
    @action(
        detail=True,
        methods=["patch"],
        permission_classes=[IsSuperAdminOrAdmin]
    )
    def verify(self, request, pk=None):

        inspection = self.get_object()

        if inspection.status == "verified":
            return Response(
                {"detail": "Inspection is already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )

        InspectionService.verify_inspection(
            inspection=inspection,
            user=request.user,
            status_value=request.data.get("status"),
            admin_remarks=request.data.get("admin_remarks", "")
        )

        return Response(
            {"detail": "Inspection updated successfully."},
            status=status.HTTP_200_OK
        )

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
        "user__profile",
        "created_by"
    )

    permission_classes = [IsAuthenticated, IsSuperAdminOrAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateInspectorSerializer

        return InspectorSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        inspector = InspectorService.create_inspector(
            admin_user=request.user,
            validated_data=serializer.validated_data
        )

        return Response(
            InspectorSerializer(inspector).data,
            status=status.HTTP_201_CREATED
        )


