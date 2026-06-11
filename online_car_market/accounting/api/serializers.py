from rest_framework import serializers
from rolepermissions.checkers import has_role
from ..models import Expense, FinancialReport, CarExpense, Revenue, ExchangeRate
from online_car_market.sales.models import Sale
import bleach

class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = "__all__"

    def validate_rate(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Exchange rate must be greater than zero."
            )
        if value > 1000:
            raise serializers.ValidationError(
                "Exchange rate seems unreasonably high."
            )
        return value

    def validate(self, data):
        date = data.get("date")

        if ExchangeRate.objects.filter(date=date).exclude(
            pk=self.instance.pk if self.instance else None
        ).exists():
            raise serializers.ValidationError(
                "An exchange rate for this date already exists."
            )

        return data

class CarExpenseSerializer(serializers.ModelSerializer):
    vin_code = serializers.CharField(source="car.vin", read_only=True)
    origin = serializers.CharField(source="car.origin", read_only=True)

    class Meta:
        model = CarExpense
        fields = '__all__'
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

class RevenueSerializer(serializers.ModelSerializer):
    source_type = serializers.ChoiceField(
        choices=['sale', 'broker_payment'],
        write_only=True
    )
    source_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Revenue
        fields = [
            'dealer',
            'source',
            'source_type',
            'source_id',
            'amount',
            'description',
            'currency',
            'converted_amount',
            'invoice_number',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'source',
            'invoice_number',
            'converted_amount',
            'created_at'
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Revenue amount must be greater than zero.")
        return value

    def validate(self, data):
        source_type = data.get('source_type')
        source_id = data.get('source_id')
        amount = data.get('amount')
        currency = data.get('currency')

        # Validate source mapping
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

        else:
            raise serializers.ValidationError("Invalid source type.")

        # Currency conversion
        if currency == 'USD':
            rate = ExchangeRate.objects.filter(
                from_currency='USD',
                to_currency='ETB'
            ).order_by('-date').first()

            if not rate:
                raise serializers.ValidationError("No exchange rate available for USD to ETB.")

            data['converted_amount'] = amount * rate.rate

        elif currency == 'ETB':
            data['converted_amount'] = amount

        else:
            raise serializers.ValidationError("Unsupported currency for conversion.")

        return data

class ExpenseSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(
        source="company.company_name",
        read_only=True
    )

    company = serializers.PrimaryKeyRelatedField(
        queryset=DealerProfile.objects.all(),
        required=False
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "company",
            "company_name",
            "type",
            "amount",
            "description",
            "currency",
            "exchange_rate",
            "invoice_number",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "invoice_number",
            "exchange_rate",
            "created_at",
        ]

    def validate_type(self, value):
        cleaned_value = bleach.clean(
            value.strip(),
            tags=[],
            strip=True
        )

        if not cleaned_value:
            raise serializers.ValidationError(
                "Type cannot be empty."
            )

        if len(cleaned_value) > 100:
            raise serializers.ValidationError(
                "Type cannot exceed 100 characters."
            )

        return cleaned_value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero."
            )

        if value > 100000000:
            raise serializers.ValidationError(
                "Amount cannot exceed 100,000,000."
            )

        return value

    def validate_description(self, value):
        if value:
            cleaned_value = bleach.clean(
                value.strip(),
                tags=[],
                strip=True
            )

            if len(cleaned_value) > 1000:
                raise serializers.ValidationError(
                    "Description cannot exceed 1000 characters."
                )

            return cleaned_value

        return value

    def validate_currency(self, value):
        valid_currencies = ["ETB", "USD"]

        if value not in valid_currencies:
            raise serializers.ValidationError(
                "Currency must be ETB or USD."
            )

        return value

    def validate(self, attrs):
        """
        Handle exchange rate assignment.
        Works for both create and partial update.
        """

        currency = attrs.get(
            "currency",
            getattr(self.instance, "currency", None)
        )

        if currency == "USD":
            rate = ExchangeRate.objects.filter(
                from_currency="USD",
                to_currency="ETB"
            ).order_by("-date").first()

            if not rate:
                raise serializers.ValidationError(
                    "No USD to ETB exchange rate available."
                )

            attrs["exchange_rate"] = rate.rate

        elif currency == "ETB":
            attrs["exchange_rate"] = 1

        return attrs

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
