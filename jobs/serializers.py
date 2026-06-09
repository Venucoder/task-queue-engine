from rest_framework import serializers
from .models import Job

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id', 'task_type', 'payload', 'status', 'priority', 'result', 'retry_count', 'created_at']
        read_only_fields = ['id', 'status', 'result', 'retry_count', 'created_at']