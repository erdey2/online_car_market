from django.utils import timezone
from django.db import transaction
from rolepermissions.roles import assign_role, remove_role
from online_car_market.brokers.models import BrokerProfile

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

    remove_role(broker.profile.user, 'broker')
    assign_role(broker.profile.user, 'broker')


@transaction.atomic
def reject_broker(broker, admin_user, reason):
    if broker.status != BrokerProfile.Status.PENDING:
        raise ValueError("Only pending brokers can be rejected")


    broker.status = BrokerProfile.Status.REJECTED
    broker.reviewed_at = timezone.now()
    broker.reviewed_by = admin_user
    broker.rejection_reason = reason
    broker.save()

    remove_role(broker.profile.user, 'broker')


@transaction.atomic
def suspend_broker(broker, admin_user):
    if broker.status != BrokerProfile.Status.APPROVED:
        raise ValueError("Only approved brokers can be suspended")

    broker.status = BrokerProfile.Status.SUSPENDED
    broker.reviewed_at = timezone.now()
    broker.reviewed_by = admin_user
    broker.save()

    remove_role(broker.profile.user, 'broker')


@transaction.atomic
def reactivate_broker(broker, admin_user):
    if broker.status != BrokerProfile.Status.SUSPENDED:
        raise ValueError("Only suspended brokers can be reactivated")

    broker.status = BrokerProfile.Status.APPROVED
    broker.reviewed_at = timezone.now()
    broker.reviewed_by = admin_user
    broker.rejection_reason = None
    broker.save()

    assign_role(broker.profile.user, 'broker')
