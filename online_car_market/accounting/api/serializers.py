from rest_framework import serializers
from rolepermissions.checkers import has_role
from ..models import Expense, FinancialReport
import bleach


class ExpenseSerializer(serializers.ModelSerializer):
    # Explicitly define `type` so schema shows choices
    type = serializers.ChoiceField(
        choices=Expense._meta.get_field('type').choices,
        help_text="Expense type. Options: maintenance, marketing, operational, other"
    )

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
            raise serializers.ValidationError(
                "Only accountant, dealer, admins, or super admins can manage expenses."
            )
        return data


class FinancialReportSerializer(serializers.ModelSerializer):
    # Explicitly define `type` field so schema shows enum
    type = serializers.ChoiceField(
        choices=FinancialReport._meta.get_field('type').choices,
        help_text="Financial report type. Options: profit_loss, balance_sheet"
    )

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
        report_type = self.initial_data.get('type')
        required_keys = (
            {'total_revenue', 'total_expenses', 'net_profit'}
            if report_type == 'profit_loss'
            else {'assets', 'liabilities', 'equity'}
        )

        sanitized_data = {}
        for key, val in value.items():
            sanitized_data[key] = bleach.clean(val.strip(), tags=[], strip=True) if isinstance(val, str) else val

        for key in required_keys:
            if key not in sanitized_data:
                raise serializers.ValidationError(f"Data must include '{key}' key.")
            if not isinstance(sanitized_data[key], (int, float)) or sanitized_data[key] < 0:
                raise serializers.ValidationError(f"'{key}' must be a non-negative number.")

        if report_type == 'profit_loss':
            if sanitized_data['net_profit'] != sanitized_data['total_revenue'] - sanitized_data['total_expenses']:
                raise serializers.ValidationError(
                    "Net profit must equal total revenue minus total expenses for profit_loss reports."
                )

        return sanitized_data

    def validate(self, data):
        """Ensure only accounting, admins, or super admins can create/update reports."""
        user = self.context['request'].user
        if not has_role(user, ['super_admin', 'admin', 'accountant']):
            raise serializers.ValidationError(
                "Only accounting, admins, or super admins can manage financial reports."
            )
        return data
