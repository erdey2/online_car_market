from rest_framework import serializers

class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

# Serializer for success response
class OTPResponseSerializer(serializers.Serializer):
    message = serializers.CharField()

# Serializer for error response
class OTPErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()

class ConfirmOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

# Serializer for success response
class ConfirmPasswordResetSuccessSerializer(serializers.Serializer):
    message = serializers.CharField()

# Serializer for error response
class ConfirmErrorResponseSerializer(serializers.Serializer):
    error = serializers.CharField()
