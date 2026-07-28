from online_car_market.notifications.services import notify_user
from online_car_market.users.models import User


class CarRequestNotificationService:

    @staticmethod
    def _admins():
        return User.objects.filter(
            role__in=[
                User.Role.ADMIN,
                User.Role.SUPER_ADMIN,
            ]
        ).only("id")

    @staticmethod
    def _notify_admins(message, data):
        for admin in CarRequestNotificationService._admins():
            notify_user(
                user=admin,
                message=message,
                data=data,
            )

    @staticmethod
    def notify_new_request(request_obj, request_type, extra_data=None):
        data = {
            "type": f"new_{request_type}_request",
            "request_id": request_obj.id,
            f"{request_type}_name": request_obj.requested_name,
        }

        if extra_data:
            data.update(extra_data)

        CarRequestNotificationService._notify_admins(
            message=(
                f"New car {request_type} request: "
                f"{request_obj.requested_name}"
            ),
            data=data,
        )

    @staticmethod
    def notify_request_approved(request_obj, request_type):
        notify_user(
            user=request_obj.requested_by,
            message=(
                f"Your {request_type} request "
                f"'{request_obj.requested_name}' "
                f"has been approved."
            ),
            data={
                "type": f"{request_type}_request_approved",
                "request_id": request_obj.id,
            },
        )

    @staticmethod
    def notify_request_rejected(request_obj, request_type):
        notify_user(
            user=request_obj.requested_by,
            message=(
                f"Your {request_type} request "
                f"'{request_obj.requested_name}' "
                f"has been rejected."
            ),
            data={
                "type": f"{request_type}_request_rejected",
                "request_id": request_obj.id,
                "reason": request_obj.rejection_reason,
            },
        )
