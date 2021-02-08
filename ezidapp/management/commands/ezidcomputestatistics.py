import django.core.management

import impl.stats


class Command(django.core.management.BaseCommand):
    help = "Compute identifier statistics"

    def handle(self, *args, **options):
        impl.stats.recomputeStatistics()
