from rest_framework.generics import ListAPIView
from online_car_market.payroll.models import PayrollItem, Employee, SalaryComponent, EmployeeSalary, OvertimeEntry
from online_car_market.payroll.api.serializers import (EmployeeSerializer, SalaryComponentSerializer,
                                                       PayslipSerializer, PayrollRunSerializer,
                                                       EmployeeSalarySerializer, OvertimeSerializer
                                                       )
from online_car_market.payroll.selectors.payroll_queries import get_latest_payslip
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.core.exceptions import ValidationError

from online_car_market.payroll.models import PayrollRun
from online_car_market.payroll.services.payroll_runner import run_payroll

class PayrollRunViewSet(viewsets.ModelViewSet):
    queryset = PayrollRun.objects.all().order_by("-created_at")
    serializer_class = PayrollRunSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        payroll_run = self.get_object()

        try:
            result = run_payroll(payroll_run)
        except ValidationError as e:
            # Friendly API error if payroll is posted
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            # Other business rule errors
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"detail": "Payroll processed successfully", "data": result},
            status=status.HTTP_200_OK
        )

class PayslipAPIView(ListAPIView):
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        payslip = get_latest_payslip(self.request.user.employee)
        return PayrollItem.objects.filter(id=payslip.id) if payslip else PayrollItem.objects.none()

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAdminUser]

class SalaryComponentViewSet(viewsets.ModelViewSet):
    queryset = SalaryComponent.objects.all()
    serializer_class = SalaryComponentSerializer
    permission_classes = [IsAdminUser]

class EmployeeSalaryViewSet(ModelViewSet):
    queryset = EmployeeSalary.objects.select_related(
        "employee", "component"
    )
    serializer_class = EmployeeSalarySerializer
    permission_classes = [IsAdminUser]

class OvertimeEmployeeViewSet(ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = OvertimeSerializer
    queryset = OvertimeEntry.objects.all()





