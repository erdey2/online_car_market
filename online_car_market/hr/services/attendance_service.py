from decimal import Decimal
from datetime import date, timedelta
from ..models import Attendance, Leave

class AttendanceService:

    STANDARD_DAILY_HOURS = Decimal("8.0")

    @staticmethod
    def monthly_employee_summary(year, month, employee):
        """
        Payroll-ready monthly analytics for a single employee, including:
        - Total actual hours worked
        - Total payable hours (capped per day)
        - Overtime hours
        - Deficit / absent hours
        - Total working days, present days, absent days
        - Sundays are treated as 'automatic present' (not counted as absent)
        """

        # Get all Attendance records for the month
        records = Attendance.objects.filter(
            employee=employee,
            date__year=year,
            date__month=month
        )

        # Map of date -> Attendance
        attendance_map = {att.date: att for att in records}

        total_actual_hours = Decimal("0.00")
        total_payable_hours = Decimal("0.00")
        present_days = 0
        absent_days = 0

        # Compute expected working days excluding Sundays
        expected_days = AttendanceService.working_days_in_month(year, month)

        # Iterate over all days in the month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        for single_day in (start_date + timedelta(days=i) for i in range((end_date - start_date).days)):
            if single_day.weekday() == 6:  # Sunday
                # Automatically count Sunday as "present" but no hours
                continue

            att = attendance_map.get(single_day)
            if att and att.entry_time and att.exit_time and att.status == "present":
                # Compute hours for this day
                entry_dt = att.entry_time
                exit_dt = att.exit_time

                if exit_dt <= entry_dt:
                    continue

                seconds = Decimal(str((exit_dt - entry_dt).total_seconds()))
                actual_hours = seconds / Decimal("3600")
                capped_hours = min(actual_hours, AttendanceService.STANDARD_DAILY_HOURS)

                total_actual_hours += actual_hours
                total_payable_hours += capped_hours
                present_days += 1
            else:
                # Day with no record or not present -> count as absent
                absent_days += 1

        # Deficit and overtime
        expected_hours = expected_days * AttendanceService.STANDARD_DAILY_HOURS
        deficit_hours = max(Decimal("0.00"), expected_hours - total_payable_hours)
        overtime_hours = max(Decimal("0.00"), total_actual_hours - total_payable_hours)

        return {
            "year": year,
            "month": month,
            "employee_id": employee.id,
            "expected_working_days": expected_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "total_actual_hours": round(total_actual_hours, 2),
            "total_payable_hours": round(total_payable_hours, 2),
            "absent_hours": round(deficit_hours, 2),
            "overtime_hours": round(overtime_hours, 2),
            "standard_daily_hours": AttendanceService.STANDARD_DAILY_HOURS,
        }

    @staticmethod
    def working_days_in_month(year, month):
        """Return number of working days in a month (excluding Sundays)."""
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1)
        else:
            end = date(year, month + 1, 1)

        days = 0
        current = start
        while current < end:
            if current.weekday() != 6:  # Exclude Sundays
                days += 1
            current += timedelta(days=1)
        return days
