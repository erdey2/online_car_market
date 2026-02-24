from decimal import Decimal
from datetime import date, timedelta
from ..models import Attendance, Leave

class AttendanceService:

    STANDARD_DAILY_HOURS = Decimal("8.0")

    @staticmethod
    def monthly_employee_summary(year, month, employee):
        """
        Payroll-ready monthly analytics for a single employee.
        - Missing Attendance on working days counts as absent
        - Approved leaves are not counted as absent
        - Sundays are skipped
        """
        # All attendance records for the month
        records = Attendance.objects.filter(
            employee=employee,
            date__year=year,
            date__month=month,
            status="present"
        )

        # Map date -> attendance record
        attendance_map = {rec.date: rec for rec in records}

        # Approved leaves in the month
        leaves = Leave.objects.filter(
            employee=employee,
            status="approved",
            start_date__lte=date(year, month, 31),
            end_date__gte=date(year, month, 1)
        )

        # Map all leave dates to True
        leave_days = set()
        for leave in leaves:
            current = max(leave.start_date, date(year, month, 1))
            end = min(leave.end_date, date(year, month, 31))
            while current <= end:
                leave_days.add(current)
                current += timedelta(days=1)

        total_actual_hours = Decimal("0.0")
        total_capped_hours = Decimal("0.0")
        present_days = 0
        absent_days = 0
        leave_count = 0

        # Iterate all days in the month
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        current = start

        while current < end:
            if current.weekday() == 6:  # Skip Sundays
                current += timedelta(days=1)
                continue

            if current in leave_days:
                leave_count += 1
            else:
                record = attendance_map.get(current)
                if record:
                    entry = record.entry_time
                    exit = record.exit_time
                    if exit <= entry:
                        actual_hours = Decimal("0.0")
                    else:
                        seconds = Decimal(str((exit - entry).total_seconds()))
                        actual_hours = seconds / Decimal("3600")
                    capped_hours = min(actual_hours, AttendanceService.STANDARD_DAILY_HOURS)
                    total_actual_hours += actual_hours
                    total_capped_hours += capped_hours
                    present_days += 1
                else:
                    # No record and no leave = absent
                    absent_days += 1

            current += timedelta(days=1)

        total_working_days = present_days + absent_days + leave_count
        expected_hours = total_working_days * AttendanceService.STANDARD_DAILY_HOURS
        overtime_hours = max(Decimal("0.0"), total_actual_hours - total_capped_hours)
        deficit_hours = max(Decimal("0.0"), expected_hours - total_capped_hours)

        return {
            "year": year,
            "month": month,
            "employee_id": employee.id,
            "total_working_days": total_working_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "leave_days": leave_count,
            "total_actual_hours": round(total_actual_hours, 2),
            "total_payable_hours": round(total_capped_hours, 2),
            "overtime_hours": round(overtime_hours, 2),
            "deficit_hours": round(deficit_hours, 2),
            "standard_daily_hours": AttendanceService.STANDARD_DAILY_HOURS,
        }
