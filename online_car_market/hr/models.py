from django.db import models
from django.utils import timezone
from cloudinary.models import CloudinaryField
from online_car_market.users.models import User, Profile  # Import from users app
from django.utils.translation import gettext_lazy as _

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    hire_date = models.DateField(default=timezone.now)
    position = models.CharField(max_length=100, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.position or 'Employee'}"

    class Meta:
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'

CONTRACT_STATUS = [
    ("draft", "Draft"),
    ("submitted", "Submitted by Employee"),
    ("approved", "Approved by HR"),
    ("rejected", "Rejected by HR"),
    ("active", "Active"),
    ("terminated", "Terminated"),
]

class Contract(models.Model):
    employee = models.ForeignKey("hr.Employee", on_delete=models.CASCADE, related_name="contracts")
    job_title = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    probation_days = models.PositiveIntegerField(default=60)

    gross_salary = models.DecimalField(max_digits=12, decimal_places=2)
    transport_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    terms = models.TextField(blank=True)
    hours_of_work = models.CharField(max_length=255, blank=True, default="Mon-Sat 9:00-17:00")
    annual_leave = models.CharField(max_length=255, blank=True, default="16 days first year")

    signed_pdf = models.FileField(upload_to="contracts/signed_pdfs/", null=True, blank=True)
    employee_signature = models.ImageField(upload_to="contracts/signatures/employees/", null=True, blank=True)
    hr_signature = models.ImageField(upload_to="contracts/signatures/hr/", null=True, blank=True)
    company_stamp = models.ImageField(upload_to="contracts/stamps/", null=True, blank=True)

    status = models.CharField(max_length=20, choices=CONTRACT_STATUS, default="draft")
    uploaded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="uploaded_contracts")
    uploaded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Contract #{self.id} for {self.employee} [{self.status}]"

    class Meta:
        ordering = ["-created_at"]

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    entry_time = models.DateTimeField(null=True, blank=True)
    exit_time = models.DateTimeField(null=True, blank=True)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=[('present', 'Present'), ('absent', 'Absent'), ('leave', 'Leave')], default='present')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Attendance for {self.employee.user.email} on {self.date}"

    class Meta:
        unique_together = ('employee', 'date')
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendances'

class Leave(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('denied', 'Denied')], default='pending')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='leave_approvals')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Leave for {self.employee.user.email} from {self.start_date} to {self.end_date} - {self.status}"

    class Meta:
        verbose_name = 'Leave'
        verbose_name_plural = 'Leaves'
