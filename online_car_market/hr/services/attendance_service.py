from datetime import datetime, timedelta, date
from decimal import Decimal
from ..models import Attendance


class AttendanceService:

    STANDARD_DAILY_HOURS = Decimal("8.0")

    @staticmethod
    def monthly_working_hours(year, month, employee=None):
        """
        Calculate total worked hours for a given month.
        - Excludes Sundays
        - Uses Decimal for payroll safety
        """

        queryset = Attendance.objects.filter(
            date__year=year,
            date__month=month,
            entry_time__isnull=False,
            exit_time__isnull=False,
            status="present"
        )

        if employee:
            queryset = queryset.filter(employee=employee)

        total_hours = Decimal("0.00")
        total_working_days = 0

        for record in queryset:

            # Exclude Sundays using the official date field
            if record.date.weekday() == 6:
                continue

            entry_dt = record.entry_time
            exit_dt = record.exit_time

            # Ignore invalid records
            if exit_dt <= entry_dt:
                continue

            seconds = Decimal(str((exit_dt - entry_dt).total_seconds()))
            actual_hours = seconds / Decimal("3600")

            counted_hours = min(
                actual_hours,
                AttendanceService.STANDARD_DAILY_HOURS
            )

            total_hours += counted_hours
            total_working_days += 1

        return {
            "year": year,
            "month": month,
            "total_worked_hours": total_hours,
            "total_working_days": total_working_days,
            "standard_daily_hours": AttendanceService.STANDARD_DAILY_HOURS,
        }

    @staticmethod
    def working_days_in_month(year, month):
        """
        Returns number of working days in a month (excluding Sundays).
        """

        start = date(year, month, 1)

        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)

        days = 0
        current = start

        while current < end:
            if current.weekday() != 6:  # Exclude Sunday
                days += 1
            current += timedelta(days=1)

        return days
