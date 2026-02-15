from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.functions import Lower

from online_car_market.inventory.models import Car
from online_car_market.users.models import User
from online_car_market.brokers.models import BrokerProfile
from online_car_market.dealers.models import DealerProfile

class Sale(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    buyer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='purchases')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    broker = models.ForeignKey(BrokerProfile, on_delete=models.SET_NULL, null=True, blank=True)
    dealer = models.ForeignKey(DealerProfile, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Sale of {self.car} on {self.date}"

class Lead(models.Model):

    class LeadStatus(models.TextChoices):
        INQUIRY = "inquiry", "Inquiry"
        CONTACTED = "contacted", "Contacted"
        NEGOTIATION = "negotiation", "Negotiation"
        CLOSED = "closed", "Closed"
        LOST = "lost", "Lost"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=100)

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="buyer_leads"
    )

    contact = models.CharField(max_length=100)  # email or phone

    status = models.CharField(
        max_length=20,
        choices=LeadStatus.choices,
        default=LeadStatus.INQUIRY
    )

    assigned_sales = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads"
    )

    car = models.ForeignKey("inventory.Car", on_delete=models.CASCADE, related_name="leads")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_leads"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("contact"),
                "car",
                name="unique_lead_contact_per_car_ci"
            )
        ]

        indexes = [
            models.Index(fields=["contact"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.status}"

    # Business Logic
    def mark_closed(self, user):
        self.status = self.LeadStatus.CLOSED
        self.closed_at = timezone.now()
        self.closed_by = user
        self.save()

        # automatically mark car as sold
        if self.car and self.car.status == "available":
            self.car.status = "sold"
            self.car.sold_at = timezone.now()
            self.car.save()
