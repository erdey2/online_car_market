from django.db import models
from online_car_market.dealers.models import DealerProfile
from django.utils import timezone
from online_car_market.inventory.models import Car

# Financial Report
class Currency(models.TextChoices):
    USD = 'USD', 'US Dollar'
    ETB = 'ETB', 'Ethiopian Birr'

class ExchangeRate(models.Model):
    """Stores exchange rates for USD -> ETB conversion."""
    rate = models.DecimalField(max_digits=10, decimal_places=2)  # e.g., 130.50 ETB/USD
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"1 USD = {self.rate} ETB ({self.date})"

class Expense(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='expenses', null=True, blank=True)
    type = models.CharField(max_length=100, choices=[
        ('purchase', 'Purchase'),
        ('shipping', 'Shipping'),
        ('tax', 'Tax'),
        ('maintenance', 'Maintenance'),
        ('marketing', 'Marketing'),
        ('salary', 'Salary'),
        ('operational', 'Operational'),
        ('other', 'Other')
    ])
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, choices=[('USD', 'USD'), ('ETB', 'ETB')], default='ETB')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # store rate used for conversion
    date = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.type} - {self.amount} ({self.dealer}) on {self.date}"

class CarExpense(models.Model):
    """Expense related to a specific car purchase."""
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='car_expenses')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='expenses')
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)
    converted_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    date = models.DateField(default=timezone.now)

    def save(self, *args, **kwargs):
        """Automatically convert to ETB when in USD."""
        if self.currency == Currency.USD:
            latest_rate = ExchangeRate.objects.order_by('-date').first()
            if latest_rate:
                self.converted_amount = self.amount * latest_rate.rate
        else:
            self.converted_amount = self.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.car} - {self.description} ({self.amount} {self.currency})"

class Revenue(models.Model):
    """Tracks income sources."""
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='revenues')
    source = models.CharField(max_length=100, choices=[
        ('car_sale', 'Car Sale'),
        ('broker_fee', 'Broker Fee'),
        ('other', 'Other'),
    ])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.ETB)
    converted_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if self.currency == Currency.USD:
            latest_rate = ExchangeRate.objects.order_by('-date').first()
            if latest_rate:
                self.converted_amount = self.amount * latest_rate.rate
        else:
            self.converted_amount = self.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source} - {self.amount} {self.currency} ({self.dealer})"

class FinancialReport(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='financial_reports', null=True, blank=True)
    type = models.CharField(max_length=50, choices=[
        ('profit_loss', 'Profit/Loss'),
        ('balance_sheet', 'Balance Sheet')
    ])
    data = models.JSONField()  # Store report data as JSON
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} Report - {self.created_at}"
