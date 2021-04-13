import django.core.management

import impl.daemon.stats


class Command(django.core.management.BaseCommand):
    help = "Compute identifier statistics"

    def handle(self, *args, **options):
        impl.daemon.stats.recomputeStatistics()
