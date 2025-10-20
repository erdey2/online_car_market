from rest_framework import serializers
from rolepermissions.checkers import has_role
from ..models import Expense, FinancialReport
import re
import bleach

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['id', 'type', 'amount', 'dealer', 'date', 'description']
        read_only_fields = ['id', 'date']

    def validate_type(self, value):
        """Validate and sanitize type."""
        valid_types = ['maintenance', 'marketing', 'operational', 'other']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_types:
            raise serializers.ValidationError(f"Type must be one of: {', '.join(valid_types)}.")
        return cleaned_value

    def validate_amount(self, value):
        """Ensure amount is non-negative and reasonable."""
        if value < 0:
            raise serializers.ValidationError("Amount cannot be negative.")
        if value > 100000000:
            raise serializers.ValidationError("Amount cannot exceed 100,000,000.")
        return value

    def validate_description(self, value):
        """Sanitize and validate description."""
        if value:
            cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
            if len(cleaned_value) > 1000:
                raise serializers.ValidationError("Description cannot exceed 1000 characters.")
            return cleaned_value
        return value

    def validate(self, data):
        """Ensure only accounting, admins, or super admins can create/update expenses."""
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin', 'dealer', 'accountant']):
            raise serializers.ValidationError("Only accountant, dealer, admins, or super admins can manage expenses.")
        return data

class FinancialReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialReport
        fields = ['id', 'type', 'dealer', 'data', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_type(self, value):
        """Validate and sanitize type."""
        valid_types = ['profit_loss', 'balance_sheet']
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if cleaned_value not in valid_types:
            raise serializers.ValidationError(f"Type must be one of: {', '.join(valid_types)}.")
        return cleaned_value

    def validate_data(self, value):
        """Validate and sanitize JSON data."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Data must be a valid JSON object.")
        required_keys = {'total_revenue', 'total_expenses', 'net_profit'} if self.initial_data.get('type') == 'profit_loss' else {'assets', 'liabilities', 'equity'}
        sanitized_data = {}
        for key in value:
            if isinstance(value[key], str):
                sanitized_data[key] = bleach.clean(value[key].strip(), tags=[], strip=True)
            else:
                sanitized_data[key] = value[key]
        for key in required_keys:
            if key not in sanitized_data:
                raise serializers.ValidationError(f"Data must include '{key}' key.")
            if not isinstance(sanitized_data[key], (int, float)) or sanitized_data[key] < 0:
                raise serializers.ValidationError(f"'{key}' must be a non-negative number.")
        if sanitized_data.get('total_revenue') and sanitized_data.get('total_expenses') and sanitized_data.get('net_profit'):
            if sanitized_data['net_profit'] != sanitized_data['total_revenue'] - sanitized_data['total_expenses']:
                raise serializers.ValidationError("Net profit must equal total revenue minus total expenses for profit_loss reports.")
        return sanitized_data

    def validate(self, data):
        """Ensure only accounting, admins, or super admins can create/update reports."""
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin', 'accounting']):
            raise serializers.ValidationError("Only accounting, admins, or super admins can manage financial reports.")
        return data
