from django.utils import timezone
from django.db import transaction
from online_car_market.brokers.models import BrokerProfile
from online_car_market.notifications.services import notify_user

# Broker Services with Transactions
@transaction.atomic
def approve_broker(broker: BrokerProfile, admin_user):
    if broker.status != BrokerProfile.Status.PENDING:
        raise ValueError("Only pending brokers can be approved")

    broker.status = BrokerProfile.Status.APPROVED
    broker.reviewed_at = timezone.now()
    broker.reviewed_by = admin_user
    broker.rejection_reason = None
    broker.save()

    # Assign role
    user = broker.profile.user
    user.role = user.Role.BROKER
    user.save(update_fields=["role"])

    # Notification
    notify_user(
        user=user,
        message="Your broker application has been approved!",
        data={
            "type": "broker_approved",
            "broker_id": broker.id,
            "broker_name": broker.get_display_name(),
        }
    )

@transaction.atomic
def reject_broker(broker, admin_user, reason):
    if broker.status != BrokerProfile.Status.PENDING:
        raise ValueError("Only pending brokers can be rejected")

    broker.status = BrokerProfile.Status.REJECTED
    broker.reviewed_at = timezone.now()
    broker.reviewed_by = admin_user
    broker.rejection_reason = reason
    broker.save()

    user = broker.profile.user
    user.role = user.Role.BUYER
    user.save(update_fields=["role"])

    # NOTIFICATION
    notify_user(
        user=user,
        message=f"Your broker application was rejected: {reason}",
        data={
            "type": "broker_rejected",
            "reason": reason,
        }
    )

@transaction.atomic
def suspend_broker(broker, admin_user):
    if broker.status != BrokerProfile.Status.APPROVED:
        raise ValueError("Only approved brokers can be suspended")

    broker.status = BrokerProfile.Status.SUSPENDED
    broker.reviewed_at = timezone.now()
    broker.reviewed_by = admin_user
    broker.save()

    user = broker.profile.user
    user.role = user.Role.BUYER
    user.save()

@transaction.atomic
def reactivate_broker(broker, admin_user):
    if broker.status != BrokerProfile.Status.SUSPENDED:
        raise ValueError("Only suspended brokers can be reactivated")

    broker.status = BrokerProfile.Status.APPROVED
    broker.reviewed_at = timezone.now()
    broker.reviewed_by = admin_user
    broker.rejection_reason = None
    broker.save()

    user = broker.profile.user
    user.role = user.Role.BROKER
    user.save()
