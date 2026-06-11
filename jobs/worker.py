import os
import sys
import logging
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

def process_job(job_id):
    # Get a job from DB
    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.error(f"Job {job_id} does not exist")

    logger.info(f"Processing job {job_id} | task_type: {job.task_type} | priority: {job.priority}")

    # Set Job status as processing
    job.status = Job.Status.PROCESSING
    job.save()

    # Get Handler based on task_type and check if it exists
    handler = TASK_REGISTRY.get(job.task_type)
    if not handler:
        job.status = Job.Status.FAILED
        job.result = {"error": f"Unknown task type {job.task_type}"}
        job.save()
        logger.error(f"No handler found for task type {job.task_type}")
        return

    # If exists run the task with handler and save the result in the DB
    try:
        result = handler(job.payload)
        job.result = result
        job.status = Job.Status.DONE
        job.save()
        logger.info(f"Job {job_id} completed successfully")
    except Exception as e:
        job.status = Job.Status.FAILED
        job.result = {"error": str(e)}
        job.save()
        logger.info(f"Job {job_id} failed with error: {str(e)}")

def run_worker():
    logger.info(f"Worker started. Listening to Queues: {QUEUES}")

    # Continuously listen to the queues to fetch the tasks with BLPOP
    while True:
        # BLPOP blocks until job appears - timeout=30 means it wakes up every 30 seconds even if empty, just to stay alive
        result = redis_client.blpop(QUEUES, timeout=30)
        if not result:
            logger.info("No jobs in the queue, Waiting...")
            continue

        queue_name, job_id_bytes = result
        job_id = int(job_id_bytes.decode('utf-8'))
        logger.info(f"Picked up job {job_id} from queue: {queue_name.decode()}")
        process_job(job_id)

if __name__ == "__main__":
    run_worker()
