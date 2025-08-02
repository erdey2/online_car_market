from rest_framework import serializers
from rolepermissions.checkers import has_role
from ..models import Expense, FinancialReport
import re

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['id', 'type', 'amount', 'date', 'description']
        read_only_fields = ['id', 'date']

    def validate_type(self, value):
        """Ensure type is valid."""
        valid_types = ['maintenance', 'marketing', 'operational', 'other']
        if value not in valid_types:
            raise serializers.ValidationError(f"Type must be one of: {', '.join(valid_types)}.")
        return value

    def validate_amount(self, value):
        """Ensure amount is non-negative and reasonable."""
        if value < 0:
            raise serializers.ValidationError("Amount cannot be negative.")
        if value > 100000000:  # Max 100 million
            raise serializers.ValidationError("Amount cannot exceed 100,000,000.")
        return value

    def validate_description(self, value):
        """Ensure description is within length."""
        if value and len(value) > 1000:
            raise serializers.ValidationError("Description cannot exceed 1000 characters.")
        return value

    def validate(self, data):
        """Ensure only accounting, admins, or super admins can create/update expenses."""
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin', 'accounting']):
            raise serializers.ValidationError("Only accounting, admins, or super admins can manage expenses.")
        return data

class FinancialReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialReport
        fields = ['id', 'type', 'data', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_type(self, value):
        """Ensure type is valid."""
        valid_types = ['profit_loss', 'balance_sheet']
        if value not in valid_types:
            raise serializers.ValidationError(f"Type must be one of: {', '.join(valid_types)}.")
        return value

    def validate_data(self, value):
        """Ensure data is valid JSON with required keys."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Data must be a valid JSON object.")
        required_keys = {'total_revenue', 'total_expenses', 'net_profit'} if value.get('type') == 'profit_loss' else {'assets', 'liabilities', 'equity'}
        for key in required_keys:
            if key not in value:
                raise serializers.ValidationError(f"Data must include '{key}' key.")
            if not isinstance(value[key], (int, float)) or value[key] < 0:
                raise serializers.ValidationError(f"'{key}' must be a non-negative number.")
        return value

    def validate(self, data):
        """Ensure only accounting, admins, or super admins can create/update reports."""
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin', 'accounting']):
            raise serializers.ValidationError("Only accounting, admins, or super admins can manage financial reports.")
        return data
