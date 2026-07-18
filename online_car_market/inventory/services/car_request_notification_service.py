from online_car_market.notifications.services import notify_user
from online_car_market.users.models import User


class CarRequestNotificationService:

    @staticmethod
    def notify_admins_new_make_request(request_obj):

        admins = User.objects.filter(
            role__in=[
                User.Role.ADMIN,
                User.Role.SUPER_ADMIN,
            ]
        )

        for admin in admins:
            notify_user(
                user=admin,
                message=(
                    f"New car make request: "
                    f"{request_obj.requested_name}"
                ),
                data={
                    "type": "new_make_request",
                    "request_id": request_obj.id,
                    "make_name": request_obj.requested_name,
                }
            )


    @staticmethod
    def notify_admins_new_model_request(request_obj):

        admins = User.objects.filter(
            role__in=[
                User.Role.ADMIN,
                User.Role.SUPER_ADMIN,
            ]
        )

        for admin in admins:
            notify_user(
                user=admin,
                message=(
                    f"New car model request: "
                    f"{request_obj.requested_name}"
                ),
                data={
                    "type": "new_model_request",
                    "request_id": request_obj.id,
                    "model_name": request_obj.requested_name,
                    "make": request_obj.make.name,
                }
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
            }
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
            }
        )
