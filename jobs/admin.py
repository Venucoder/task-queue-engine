from django.contrib import admin
from .models import Job

# Register your models here.
@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['id', 'task_type', 'status', 'priority', 'created_at', 'retry_count']
    list_filter = ['status', 'priority']
    search_fields = ['task_type']
