import os

import redis
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from jobs.models import Job
from jobs.serializers import JobSerializer

redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
class JobSubmitView(APIView):
    def post(self, request):
        serializer = JobSerializer(data=request.data)
        if serializer.is_valid():
            job = serializer.save()

            # Push job ID to correct queue name based on priority
            queue_name = f"queue:{job.priority}"
            redis_client.rpush(queue_name, str(job.id))

            return Response(
                JobSerializer(job).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobStatusView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(Job, id=job_id)
        return Response(JobSerializer(job).data)


class JobStatsView(APIView):
    def get(self, request):
        stats = {'pending': Job.objects.filter(status=Job.Status.PENDING).count(),
                 'processing': Job.objects.filter(status=Job.Status.PROCESSING).count(),
                 'done': Job.objects.filter(status=Job.Status.DONE).count(),
                 'failed': Job.objects.filter(status=Job.Status.FAILED).count(),
                 'redis_high_priority_queue': redis_client.llen('queue:high'),
                 'redis_normal_priority_queue': redis_client.llen('queue:normal')}

        return Response(stats)


