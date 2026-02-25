from decimal import Decimal
from datetime import date, timedelta
import calendar
from django.db.models import F, Sum, ExpressionWrapper, DurationField
from ..models import Attendance, Leave


class AttendanceService:

    STANDARD_DAILY_HOURS = Decimal("8.0")

    @staticmethod
    def monthly_employee_summary(year, month, employee):

        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        # Aggregate attendance hours in DB
        duration_expression = ExpressionWrapper(
            F("exit_time") - F("entry_time"),
            output_field=DurationField()
        )

        attendance_qs = (
            Attendance.objects
            .filter(
                employee=employee,
                date__range=(first_day, last_day),
                status="present",
                entry_time__isnull=False,
                exit_time__isnull=False
            )
            .annotate(work_duration=duration_expression)
            .exclude(work_duration__lte=timedelta(0))
        )

        aggregated = attendance_qs.aggregate(
            total_duration=Sum("work_duration")
        )

        total_duration = aggregated["total_duration"] or timedelta(0)

        total_actual_hours = Decimal(
            str(total_duration.total_seconds())
        ) / Decimal("3600")

        # Cap per day at STANDARD_DAILY_HOURS
        present_days = attendance_qs.count()

        total_capped_hours = min(
            total_actual_hours,
            present_days * AttendanceService.STANDARD_DAILY_HOURS
        )

        # Leave Days
        leaves = Leave.objects.filter(
            employee=employee,
            status="approved",
            start_date__lte=last_day,
            end_date__gte=first_day
        )

        leave_days = 0
        for leave in leaves:
            start = max(leave.start_date, first_day)
            end = min(leave.end_date, last_day)
            leave_days += (end - start).days + 1

        # Count working days (excluding Sundays)
        total_days_in_month = (last_day - first_day).days + 1

        sundays = sum(
            1
            for i in range(total_days_in_month)
            if (first_day + timedelta(days=i)).weekday() == 6
        )

        working_days = total_days_in_month - sundays

        absent_days = working_days - present_days - leave_days
        absent_days = max(0, absent_days)

        expected_hours = working_days * AttendanceService.STANDARD_DAILY_HOURS

        overtime_hours = max(
            Decimal("0.0"),
            total_actual_hours - total_capped_hours
        )

        deficit_hours = max(
            Decimal("0.0"),
            expected_hours - total_capped_hours
        )

        return {
            "year": year,
            "month": month,
            "employee_id": employee.id,
            "total_working_days": working_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "leave_days": leave_days,
            "total_actual_hours": round(total_actual_hours, 2),
            "total_payable_hours": round(total_capped_hours, 2),
            "overtime_hours": round(overtime_hours, 2),
            "deficit_hours": round(deficit_hours, 2),
            "standard_daily_hours": AttendanceService.STANDARD_DAILY_HOURS,
        }
