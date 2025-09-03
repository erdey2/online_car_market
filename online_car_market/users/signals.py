from django.db.models.signals import post_save
from django.dispatch import receiver
from online_car_market.users.models import User, Profile
from online_car_market.buyers.models import BuyerProfile, LoyaltyProgram
from online_car_market.inventory.models import Payment
from online_car_market.dealers.models import DealerRating
from online_car_market.brokers.models import BrokerRating
from rolepermissions.checkers import has_role
from rolepermissions.roles import assign_role

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        profile, _ = Profile.objects.get_or_create(user=instance)
        if not has_role(instance, ['dealer', 'broker', 'admin', 'super_admin']):
            assign_role(instance, 'Buyer')
            BuyerProfile.objects.get_or_create(profile=profile)

@receiver(post_save, sender=BuyerProfile)
def create_loyalty_program(sender, instance, created, **kwargs):
    if created:
        LoyaltyProgram.objects.get_or_create(
            buyer=instance,
            defaults={'points': instance.loyalty_points, 'reward': ''}
        )

@receiver(post_save, sender=Payment)
def update_loyalty_points_payment(sender, instance, created, **kwargs):
    if created and instance.is_confirmed and instance.payment_type == 'purchase' and has_role(instance.user, 'buyer'):
        try:
            buyer_profile = instance.user.profile.buyer_profile
            points = int(instance.amount // 100)  # 1 point per 100 units spent
            buyer_profile.loyalty_points += points
            buyer_profile.save()
            LoyaltyProgram.objects.create(
                buyer=buyer_profile,
                points=points,
                reward='' if buyer_profile.loyalty_points < 100 else 'Bronze Reward'
            )
        except BuyerProfile.DoesNotExist:
            pass

@receiver(post_save, sender=DealerRating)
@receiver(post_save, sender=BrokerRating)
def update_loyalty_points_rating(sender, instance, created, **kwargs):
    if created and has_role(instance.user, 'buyer'):
        try:
            buyer_profile = instance.user.profile.buyer_profile
            points = 10  # 10 points per rating
            buyer_profile.loyalty_points += points
            buyer_profile.save()
            LoyaltyProgram.objects.create(
                buyer=buyer_profile,
                points=points,
                reward='' if buyer_profile.loyalty_points < 100 else 'Bronze Reward'
            )
        except BuyerProfile.DoesNotExist:
            pass
