import logging
import os
import time
from datetime import timedelta

import redis
from django.utils import timezone
from dotenv import load_dotenv

from jobs.models import Job

load_dotenv()

logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(
    os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    socket_timeout=60,
    socket_connect_timeout=10
)

# How long before we consider a Job stuck
STUCK_THRESHOLD_MINUTES = 10

# How often the reaper scans
REAPER_INTERVAL_SECONDS = 60

def recover_stuck_jobs():
    cutoff_time = timezone.now() - timedelta(minutes=STUCK_THRESHOLD_MINUTES)

    # Pick all stuck jobs at processing from DB
    stuck_jobs = Job.objects.filter(
        status=Job.Status.PROCESSING,
        updated_at__lt=cutoff_time
    )

    # if there are no stuck jobs return
    if not stuck_jobs.exists():
        logger.debug("[REAPER] No stuck jobs found")
        return

    # Otherwise, we have two options, if retry count exhausted move job to dead queue else requeue
    for job in stuck_jobs:
        logger.warning(f"[REAPER] Job stuck in processing since {job.updated_at}. Requeuing")
        job.retry_count += 1

        if job.retry_count >= job.max_retries:
            logger.warning("[REAPER] Retry limit reached")
            job.status = Job.Status.DEAD
            job.result = {
                "error": "Job exceeded max retries due to worker crash",
                "final_attempt": job.retry_count
            }
            job.save()
            redis_client.rpush('queue:dead', str(job.id))
            logger.error("[REAPER] Job moved to dead letter queue")
        else:
            job.status = Job.Status.PENDING
            job.result = {
                "last_error": "Worker crashed during processing",
                "retry_count": job.retry_count
            }
            job.save()
            queue_name = f'queue:{job.priority}'
            redis_client.rpush(queue_name, str(job.id))
            logger.info(f"[REAPER] Job {job.id} queued {queue_name} (attempt {job.retry_count}/{job.max_retries})")

def run_reaper():
    logger.info(f"[REAPER] Started. Scanning every {REAPER_INTERVAL_SECONDS}s. Stuck threshold: {STUCK_THRESHOLD_MINUTES} minutes")

    while True:
        try:
            recover_stuck_jobs()
        except Exception as e:
            logger.error(f"[REAPER] Error during scan: {e}")

        time.sleep(REAPER_INTERVAL_SECONDS)


