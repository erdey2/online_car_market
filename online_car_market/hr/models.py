from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    hire_date = models.DateField(default=timezone.now)
    position = models.CharField(max_length=100, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees_created')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.position or 'Employee'}"

    class Meta:
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'

class Contract(models.Model):
    EMPLOYEE_TYPE_CHOICES = [
        ('permanent', 'Permanent'),
        ('probation', 'Probation (60 days)'),
        ('temporary', 'Temporary / Contract'),
        ('intern', 'Intern'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent_to_employee', 'Sent to Employee'),
        ('signed_by_employee', 'Signed by Employee'),
        ('active', 'Active'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    employee = models.ForeignKey('hr.Employee', on_delete=models.CASCADE, related_name='contracts')
    employee_type = models.CharField(max_length=20, choices=EMPLOYEE_TYPE_CHOICES, default='probation',
                                     help_text="Type of employment contract"
    )
    job_title = models.CharField(max_length=150)
    contract_salary = models.DecimalField(max_digits=12, decimal_places=2)
    transport_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date = models.DateField()
    probation_end_date = models.DateField(null=True, blank=True)  # Only for probation
    end_date = models.DateField(null=True, blank=True, help_text="For temporary contracts") # Optional for temporary contracts
    terms = models.TextField(blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='draft')

    # Documents
    draft_document_url = models.URLField(max_length=500, blank=True, null=True)
    employee_signed_document_url = models.URLField(max_length=500, blank=True, null=True)
    final_document_url = models.URLField(max_length=500, blank=True, null=True)

    employee_signed_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='finalized_contracts')
    finalized_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_contracts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(employee_type='probation') | models.Q(probation_end_date__isnull=True) | models.Q(
                    probation_end_date__gte=models.F('start_date')),
                name='probation_end_date_required_if_probation'
            ),
            models.CheckConstraint(
                check=models.Q(employee_type='temporary') | models.Q(end_date__isnull=True) | models.Q(
                    end_date__gte=models.F('start_date')),
                name='end_date_required_if_temporary'
            )
        ]
    def __str__(self):
        return f"{self.get_employee_type_display()} - {self.employee.user.email} ({self.job_title})"

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

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    reason = models.TextField()

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_approvals')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        email = getattr(getattr(self.employee, 'user', None), 'email', 'unknown')
        return f"Leave for {email} from {self.start_date} to {self.end_date} - {self.status}"

    class Meta:
        verbose_name = 'Leave'
        verbose_name_plural = 'Leaves'

class SalaryComponent(models.Model):
    EARNING = "earning"
    DEDUCTION = "deduction"

    COMPONENT_TYPE = [
        (EARNING, "Earning"),
        (DEDUCTION, "Deduction"),
    ]

    name = models.CharField(max_length=100)
    component_type = models.CharField(max_length=10, choices=COMPONENT_TYPE)
    is_taxable = models.BooleanField(default=True)
    is_pensionable = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class EmployeeSalary(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    component = models.ForeignKey(SalaryComponent, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("employee", "component")

class OvertimeEntry(models.Model):
    OVERTIME_TYPE_CHOICES = [
        ("1.5", "Normal Overtime (1.5x)"),
        ("1.75", "Weekend Overtime (1.75x)"),
        ("2.0", "Special Overtime (2.0x)"),
        ("2.5", "Holiday Overtime (2.5x)"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="overtime_entries")
    overtime_type = models.CharField(max_length=4, choices=OVERTIME_TYPE_CHOICES)
    hours = models.DecimalField(max_digits=6, decimal_places=2)
    approved = models.BooleanField(default=False)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]



