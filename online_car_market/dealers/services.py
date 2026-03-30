from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import DealerProfile
from online_car_market.notifications.services import notify_user

@transaction.atomic
def approve_dealer(dealer, reviewer):
    if dealer.status != DealerProfile.Status.PENDING:
        raise ValidationError("Only pending dealers can be approved.")

    dealer.status = DealerProfile.Status.APPROVED
    dealer.reviewed_by = reviewer
    dealer.reviewed_at = timezone.now()
    dealer.rejection_reason = None
    dealer.save()

    user = dealer.profile.user
    user.role = user.Role.DEALER
    user.save(update_fields=['role'])

    # CREATE NOTIFICATION
    notify_user(
        user=user,
        message="Your dealer application has been approved!",
        data={
            "type": "dealer_approved",
            "dealer_id": dealer.id,
            "company_name": dealer.company_name,
        }
    )

@transaction.atomic
def reject_dealer(dealer: DealerProfile, admin_user, reason: str):
    if dealer.status != DealerProfile.Status.PENDING:
        raise ValueError("Only pending dealers can be rejected.")

    dealer.status = DealerProfile.Status.REJECTED
    dealer.reviewed_by = admin_user
    dealer.reviewed_at = timezone.now()
    dealer.rejection_reason = reason
    dealer.save()

    user = dealer.profile.user
    user.role = user.Role.BUYER
    user.save(update_fields=["role"])

    # NOTIFICATION
    notify_user(
        user=user,
        message=f"Your dealer application was rejected: {reason}",
        data={
            "type": "dealer_rejected",
            "reason": reason,
        }
    )

@transaction.atomic
def suspend_dealer(dealer: DealerProfile, admin_user):
    if dealer.status != DealerProfile.Status.APPROVED:
        raise ValueError("Only approved dealers can be suspended.")

    dealer.status = DealerProfile.Status.SUSPENDED
    dealer.reviewed_by = admin_user
    dealer.reviewed_at = timezone.now()
    dealer.save()

    user = dealer.profile.user
    user.role = user.Role.BUYER
    user.save()

@transaction.atomic
def reactivate_dealer(dealer: DealerProfile, admin_user):
    if dealer.status != DealerProfile.Status.SUSPENDED:
        raise ValueError("Only suspended dealers can be reactivated.")

    dealer.status = DealerProfile.Status.APPROVED
    dealer.reviewed_by = admin_user
    dealer.reviewed_at = timezone.now()
    dealer.save()

    # restore role
    user = dealer.profile.user
    user.role = user.Role.DEALER
    user.save()
