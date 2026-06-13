from django.core.management import BaseCommand

from jobs.reaper import run_reaper


class Command(BaseCommand):
    help = 'Start the reaper process to recover stuck jobs'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting reaper...'))
        run_reaper()