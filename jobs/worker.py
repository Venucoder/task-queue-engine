import os
import sys
import logging
import time

import redis
import django

# Setup Django before importing models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from jobs.models import Job
from jobs.tasks import TASK_REGISTRY
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [WORKER] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    socket_timeout=60,
    socket_connect_timeout=10,
)
print("Redis ping:", redis_client.ping())

# Priority Order - worker always checks high before normal
QUEUES = ["queue:high", "queue:normal"]

def calculate_backoff(retry_count):
    """Exponential backoff: 2s, 4s, 8s, 16s..."""
    return 2 ** retry_count

def move_to_dead_letter_queue(job):
    """Job has exhausted after all retires, move to dead letter queue"""
    redis_client.rpush('queue:dead', str(job.id))
    job.status = Job.Status.DEAD
    job.save()
    logger.error(f"Job {job.id} moved to dead letter queue after {job.retry_count} retires")

def process_job(job_id, worker_id='worker-1'):
    # Get a job from DB
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.error(f"[{worker_id}] Job {job_id} does not exist")

    logger.info(f"[{worker_id}] Processing job {job_id} | task_type: {job.task_type} | priority: {job.priority} | attempt: {job.retry_count + 1}")

    # Set Job status as processing
    job.status = Job.Status.PROCESSING
    job.save()

    # Get Handler based on task_type and check if it exists
    handler = TASK_REGISTRY.get(job.task_type)
    if not handler:
        job.status = Job.Status.FAILED
        job.result = {"error": f"Unknown task type {job.task_type}"}
        job.save()
        logger.error(f"[{worker_id}] No handler found for task type {job.task_type}")
        return

    # If exists run the task with handler and save the result in the DB
    try:
        result = handler(job.payload)
        job.result = result
        job.status = Job.Status.DONE
        job.save()
        logger.info(f"[{worker_id}] Job {job_id} completed successfully")
    except Exception as e:
        # Increase Retry count
        job.retry_count += 1
        error_msg = str(e)
        logger.warning(f"[{worker_id}] Job {job_id} failed (attempt: {job.retry_count}) with error: {error_msg}")

        if job.retry_count >= job.max_retries:
            # If all retires exhausted, move the task to dead queue and update DB
            job.result = {
                "error": error_msg,
                "final_attempt": job.retry_count
            }
            job.save()
            move_to_dead_letter_queue(job)

        else:
            # Otherwise, calculate backoff and put the job status in Pending and re-queue the task
            backoff = calculate_backoff(job.retry_count)
            logger.info(f"[{worker_id}] Retrying job {job_id} in {backoff}s, (attempt: {job.retry_count}/{job.max_retries})")
            job.status = Job.Status.PENDING
            job.result = {
                "last_error": error_msg,
                "retry_count": job.retry_count,
                "next_retry_in_seconds": backoff
            }
            job.save()

            # Wait, then re-push to same priority queue
            time.sleep(backoff)
            queue_name = f"queue:{job.priority}"
            redis_client.rpush(queue_name, str(job.id))
            logger.info(f"[{worker_id}] Job {job_id} re-queued to {queue_name}")

def run_worker(worked_id='worker-1'):
    logger.info(f"[{worked_id}] Worker started. Listening to Queues: {QUEUES}")

    # Continuously listen to the queues to fetch the tasks with BLPOP
    while True:
        # BLPOP blocks until job appears - timeout=30 means it wakes up every 30 seconds even if empty, just to stay alive
        result = redis_client.blpop(QUEUES, timeout=30)
        if not result:
            logger.info(f"[{worked_id}] No jobs in the queue, Waiting...")
            continue

        queue_name, job_id_bytes = result
        job_id = int(job_id_bytes.decode('utf-8'))
        logger.info(f"[{worked_id}] Picked up job {job_id} from queue: {queue_name.decode()}")
        process_job(job_id, worked_id)
