from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from online_car_market.payroll.models import PayrollRun, PayrollItem
from online_car_market.payroll.api.serializers import PayrollRunSerializer, PayrollItemSerializer
from online_car_market.payroll.services.payroll_runner import run_payroll
from online_car_market.payroll.services.payroll_validator import can_post_payroll
from online_car_market.payroll.selectors.payroll_queries import get_payslip_for_employee
from rest_framework.permissions import IsAuthenticated

class PayrollRunViewSet(viewsets.ModelViewSet):
    queryset = PayrollRun.objects.all().order_by("-created_at")
    serializer_class = PayrollRunSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        payroll_run = self.get_object()

        try:
            run_payroll(payroll_run)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"detail": "Payroll processed successfully"},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        payroll_run = self.get_object()

        if not can_post_payroll(payroll_run):
            return Response(
                {"detail": "Payroll must be approved first"},
                status=status.HTTP_400_BAD_REQUEST
            )

        payroll_run.status = "posted"
        payroll_run.save()

        return Response(
            {"detail": "Payroll posted successfully"},
            status=status.HTTP_200_OK
        )

class PayslipViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        period = request.query_params.get("period")
        employee = request.user.employee

        payslip = get_payslip_for_employee(employee, period)

        serializer = PayrollItemSerializer(payslip, many=True)
        return Response(serializer.data)

