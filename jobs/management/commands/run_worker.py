from django.core.management import BaseCommand

from jobs.worker import run_worker


class Command(BaseCommand):
    help = "Start a job queue worker process"

    def add_arguments(self, parser):
        parser.add_argument(
            '--worker-id',
            type=str,
            default='worker-1',
            help='Unique identifier for this worker process'
        )

    def handle(self, *args, **options):
        worker_id = options.get('worker_id')
        self.stdout.write(self.style.SUCCESS(f"Starting worker [{worker_id}]"))
        run_worker(worked_id=worker_id)