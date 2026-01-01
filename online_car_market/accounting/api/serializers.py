from rest_framework import serializers
from rolepermissions.checkers import has_role
from ..models import Expense, FinancialReport, CarExpense, Revenue, ExchangeRate
from online_car_market.sales.models import Sale
from online_car_market.dealers.models import DealerProfile
import bleach

class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = '__all__'

    def validate_rate(self, value):
        """Ensure the exchange rate is positive and reasonable."""
        if value <= 0:
            raise serializers.ValidationError("Exchange rate must be greater than zero.")
        if value > 1000:  # Arbitrary upper limit to catch errors (e.g., 1 USD = 1000 ETB is plausible)
            raise serializers.ValidationError("Exchange rate seems unreasonably high. Please verify.")
        return value

    def validate(self, data):
        """Check uniqueness of currency pair and date combination."""
        date = data.get('date')
        if ExchangeRate.objects.filter(date=date).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise serializers.ValidationError("An exchange rate for this date already exists.")
        return data

    def create(self, validated_data):
        """Ensure only accountants or admins can create rates."""
        request = self.context.get('request')
        if request and not has_role(request.user, ['accountant', 'admin', 'super_admin']):
            raise serializers.ValidationError("Only accountants or admins can set exchange rates.")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Ensure only accountants or admins can update rates."""
        request = self.context.get('request')
        if request and not has_role(request.user, ['accountant', 'admin', 'super_admin']):
            raise serializers.ValidationError("Only accountants or admins can update exchange rates.")
        return super().update(instance, validated_data)

class CarExpenseSerializer(serializers.ModelSerializer):
    vin_code = serializers.CharField(source="car.vin", read_only=True)
    origin = serializers.CharField(source="car.origin", read_only=True)

    class Meta:
        model = CarExpense
        fields = '__all__'
        extra_fields = ['vin_code', 'origin']
        read_only_fields=[
            'id',
            'converted_amount',
            'invoice_number',
            'created_at',
        ]

    def validate_amount(self, value):
        """Ensure the expense amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Expense amount must be greater than zero.")
        return value

    def validate_car(self, value):
        """Ensure the car exists and is not sold."""
        if not value or value.status == 'sold':
            raise serializers.ValidationError("Expense must be linked to an available or unsold car.")
        return value

    def validate_currency(self, value):
        """Ensure currency is supported."""
        if value not in dict(CarExpense._meta.get_field('currency').choices):
            raise serializers.ValidationError("Invalid currency. Use USD or ETB.")
        return value

    def validate(self, data):
        amount = data.get('amount')
        currency = data.get('currency')

        if amount is None and currency is None:
            return data

        if amount is None or currency is None:
            raise serializers.ValidationError(
                "Both amount and currency are required."
            )

        if currency == 'USD':
            rate = ExchangeRate.objects.order_by('-date').first()
            if not rate:
                raise serializers.ValidationError("No exchange rate available.")
            data['converted_amount'] = amount * rate.rate

        elif currency == 'ETB':
            data['converted_amount'] = amount

        else:
            raise serializers.ValidationError("Unsupported currency.")

        return data

    def create(self, validated_data):
        """Ensure only accountants or dealers can create expenses."""
        request = self.context.get('request')
        if request and not has_role(request.user, ['accountant', 'dealer', 'admin', 'super_admin']):
            raise serializers.ValidationError("Only accountants or dealers can create expenses.")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Ensure only accountants or dealers can update expenses."""
        request = self.context.get('request')
        if request and not has_role(request.user, ['accountant', 'dealer', 'admin', 'super_admin']):
            raise serializers.ValidationError("Only accountants or dealers can update expenses.")
        return super().update(instance, validated_data)

class RevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revenue
        fields = [
            'dealer',
            'source',
            'amount',
            'description',
            'currency',
            'converted_amount',
            'invoice_number',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'invoice_number',
            'converted_amount',
            'created_at'
        ]

    def validate_amount(self, value):
        """Ensure the revenue amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Revenue amount must be greater than zero.")
        return value

    def validate_source_type(self, value):
        """Ensure source type is valid (e.g., 'sale' or 'broker_payment')."""
        if value not in ['sale', 'broker_payment']:
            raise serializers.ValidationError("Source type must be 'sale' or 'broker_payment'.")
        return value

    def validate(self, data):
        """Validate the source reference and convert currency if needed."""
        source_type = data.get('source_type')
        source_id = data.get('source_id')
        amount = data.get('amount')
        currency = data.get('currency')

        if source_type == 'sale':
            sale = Sale.objects.filter(id=source_id, status='sold').first()
            if not sale:
                raise serializers.ValidationError("Invalid or unsold sale reference.")
            data['source'] = sale
        elif source_type == 'broker_payment':
            payment = Payment.objects.filter(id=source_id, status='completed').first()
            if not payment:
                raise serializers.ValidationError("Invalid or uncompleted payment reference.")
            data['source'] = payment

        if currency == 'USD':
            latest_rate = ExchangeRate.objects.filter(
                from_currency='USD',
                to_currency='ETB'
            ).order_by('-date').first()
            if not latest_rate:
                raise serializers.ValidationError("No exchange rate available for USD to ETB.")
            data['converted_amount'] = amount * latest_rate.rate
        elif currency == 'ETB':
            data['converted_amount'] = amount
        else:
            raise serializers.ValidationError("Unsupported currency for conversion.")

        return data

    def create(self, validated_data):
        """Ensure only accountants or admins can create revenue entries."""
        request = self.context.get('request')
        if request and not has_role(request.user, ['accountant', 'admin', 'super_admin']):
            raise serializers.ValidationError("Only accountants or admins can create revenue entries.")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Ensure only accountants or admins can update revenue entries."""
        request = self.context.get('request')
        if request and not has_role(request.user, ['accountant', 'admin', 'super_admin']):
            raise serializers.ValidationError("Only accountants or admins can update revenue entries.")
        return super().update(instance, validated_data)

class ExpenseSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    # company = serializers.PrimaryKeyRelatedField(queryset=DealerProfile.objects.all(), required=False)
    class Meta:
        model = Expense
        fields = [
            'id',
            'company_name',
            'type',
            'amount',
            'description',
            'currency',
            'exchange_rate',
            'invoice_number',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'invoice_number',
            'exchange_rate',
            'created_at',
        ]

    def validate_type(self, value):
        """Sanitize type field."""
        cleaned_value = bleach.clean(value.strip(), tags=[], strip=True)
        if len(cleaned_value) == 0:
            raise serializers.ValidationError("Type cannot be empty.")
        if len(cleaned_value) > 100:
            raise serializers.ValidationError("Type cannot exceed 100 characters.")
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

    def validate_exchange_rate(self, value):
        """Ensure exchange rate is valid."""
        if value < 0:
            raise serializers.ValidationError("Exchange rate cannot be negative.")
        return value

    def validate(self, data):
        """Ensure correct permissions."""
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
