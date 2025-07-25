from rest_framework import serializers
from .models import FinancialReport

class FinancialReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialReport
        fields = ['id', 'type', 'data', 'created_at']
