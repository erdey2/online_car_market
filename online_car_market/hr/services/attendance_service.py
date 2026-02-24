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
        - Caps daily hours at STANDARD_DAILY_HOURS
        - Uses Decimal for payroll safety
        """

        queryset = Attendance.objects.filter(
            date__year=year,
            date__month=month,
            entry_time__isnull=False,
            exit_time__isnull=False,
        )

        if employee:
            queryset = queryset.filter(employee=employee)

        total_hours = Decimal("0.00")
        total_working_days = 0

        for record in queryset:

            # Skip Sundays (weekday() == 6)
            if record.date.weekday() == 6:
                continue

            entry_dt = datetime.combine(record.date, record.entry_time)
            exit_dt = datetime.combine(record.date, record.exit_time)

            # Ignore invalid or reversed entries
            if exit_dt <= entry_dt:
                continue

            seconds = Decimal(str((exit_dt - entry_dt).total_seconds()))
            actual_hours = seconds / Decimal("3600")

            # Cap at standard daily hours
            counted_hours = min(actual_hours, AttendanceService.STANDARD_DAILY_HOURS)

            total_hours += counted_hours
            total_working_days += 1

        return {
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
