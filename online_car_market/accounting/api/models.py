from django.db import models

# Financial Report
class FinancialReport(models.Model):
    type = models.CharField(max_length=50, choices=[
        ('profit_loss', 'Profit/Loss'),
        ('balance_sheet', 'Balance Sheet')
    ])
    data = models.JSONField()  # Store report data as JSON
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} Report - {self.created_at}"
