from django.db import models

# Create your models here.
class Job(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending'
        PROCESSING = 'processing'
        DONE = 'done'
        FAILED = 'failed'

    class Priority(models.TextChoices):
        HIGH = 'high'
        NORMAL = 'normal'

    task_type = models.CharField(max_length=100)
    priority = models.CharField(choices=Priority.choices, max_length=10, default=Priority.NORMAL)
    status = models.CharField(choices=Status.choices, max_length=20, default=Status.PENDING)
    payload = models.JSONField()
    result = models.JSONField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.task_type} | {self.status} | {self.priority}"
