from django.db.models import Count
from django.db.models.functions import TruncMonth
from ..models import Leave

class LeaveService:

    @staticmethod
    def approve_leave(leave, approved_by):
        if leave.status != Leave.Status.PENDING:
            raise ValueError("Only pending leaves can be approved")
        leave.status = Leave.Status.APPROVED
        leave.approved_by = approved_by
        leave.save()

    @staticmethod
    def reject_leave(leave, rejected_by):
        if leave.status != Leave.Status.PENDING:
            raise ValueError("Only pending leaves can be rejected")
        leave.status = Leave.Status.REJECTED
        leave.approved_by = rejected_by
        leave.save()

    @staticmethod
    def analytics(year=None, month=None):
        qs = Leave.objects.all()
        if year:
            qs = qs.filter(start_date__year=year)
        if month:
            qs = qs.filter(start_date__month=month)

        if year and not month:
            qs = qs.annotate(period=TruncMonth('start_date')).values('period', 'status')
        else:
            qs = qs.values('status')

        return qs.annotate(total=Count('id')).order_by()
