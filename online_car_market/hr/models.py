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

class Contract(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='contracts')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    terms = models.TextField(blank=True)
    contract_salary = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired'), ('terminated', 'Terminated')],
        default='draft'
    )

    signed_pdf = CloudinaryField('signed_contract', null=True, blank=True, folder='contracts/signed/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='uploaded_contracts')
    uploaded_at = models.DateTimeField(null=True, blank=True)
    employee_signature = models.ImageField(upload_to='contracts/signatures/', null=True, blank=True)
    hr_signature = models.ImageField(upload_to='contracts/hr_signatures/', null=True, blank=True)
    company_stamp = models.ImageField(upload_to='contracts/stamps/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        today = timezone.now().date()
        if self.end_date and self.end_date < today:
            self.status = 'expired'
        if self.signed_pdf and not self.uploaded_at:
            self.uploaded_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_active_contract(self):
        return self.status == 'active'

    def __str__(self):
        return f"Contract for {self.employee.user.email} ({self.start_date} - {self.end_date or 'Ongoing'})"

    class Meta:
        verbose_name = 'Contract'
        verbose_name_plural = 'Contracts'

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
