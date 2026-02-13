from rest_framework.exceptions import ValidationError
from django.utils import timezone

class InspectionService:

    @staticmethod
    def verify_inspection(inspection, user, status_value, admin_remarks):
        if status_value not in ["verified", "rejected"]:
            raise ValidationError("Invalid status. Must be 'verified' or 'rejected'.")

        inspection.status = status_value
        inspection.verified_by = user
        inspection.verified_at = timezone.now()
        inspection.admin_remarks = admin_remarks
        inspection.save()

        return inspection
