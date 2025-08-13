from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from ..models import PasswordResetOTP
from .serializers import (OTPRequestSerializer, OTPResponseSerializer, ConfirmErrorResponseSerializer,
                          OTPErrorResponseSerializer, ConfirmOTPSerializer, ConfirmPasswordResetSuccessSerializer)
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample
import random

User = get_user_model()
class RequestPasswordResetOTP(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OTPRequestSerializer,
        responses={
            200: OTPResponseSerializer,
            404: OpenApiResponse(
                response=OTPErrorResponseSerializer,
                description="User with provided email does not exist"
            ),
        },
        examples=[
            OpenApiExample(
                name="Valid Request",
                value={"email": "user@example.com"},
                request_only=True
            ),
            OpenApiExample(
                name="User Not Found",
                value={"error": "User not found"},
                response_only=True,
                status_codes=["404"]
            ),
        ],
        tags=["auth"],
        summary="Request Password Reset OTP",
        description="Send a one-time password (OTP) to the user's email for password reset."
    )
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        otp = str(random.randint(100000, 999999))
        PasswordResetOTP.objects.create(user=user, otp_code=otp)

        send_mail(
            'Your password reset code',
            f'Your OTP code is: {otp}',
            'no-reply@yourapp.com',
            [email],
        )
        return Response({'message': 'OTP sent to your email'}, status=200)


class ConfirmPasswordResetOTP(APIView):
    permission_classes = [AllowAny]
    @extend_schema(
        request=ConfirmOTPSerializer,
        responses={
            200: ConfirmPasswordResetSuccessSerializer,
            400: OpenApiResponse(response=ConfirmErrorResponseSerializer, description="Invalid OTP, expired, or other issue"),
        },
        examples=[
            OpenApiExample(
                name="Valid OTP Confirmation",
                value={
                    "email": "user@example.com",
                    "otp": "123456",
                    "new_password": "newStrongPass123"
                },
                request_only=True
            ),
            OpenApiExample(
                name="Expired OTP",
                value={"error": "OTP expired"},
                response_only=True,
                status_codes=["400"]
            ),
            OpenApiExample(
                name="Invalid OTP or Email",
                value={"error": "Invalid OTP or email"},
                response_only=True,
                status_codes=["400"]
            ),
        ],
        tags=["auth"],
        summary="Confirm Password Reset with OTP",
        description="Verify the OTP sent to user's email and allow password reset if valid."

    )
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')

        try:
            user = User.objects.get(email=email)
            otp_obj = PasswordResetOTP.objects.filter(user=user, otp_code=otp, is_used=False).latest('created_at')

            if otp_obj.is_expired():
                return Response({'error': 'OTP expired'}, status=400)

            otp_obj.is_used = True
            otp_obj.save()
            user.password = make_password(new_password)
            user.save()
            return Response({'message': 'Password reset successful'}, status=200)

        except Exception as e:
            return Response({'error': 'Invalid OTP or email'}, status=400)
