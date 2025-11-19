from django.contrib import admin
from .models import Contract

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "job_title", "status", "created_at")
    search_fields = ("employee__user__email", "job_title")
    list_filter = ("status",)

