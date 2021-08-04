import logging

import django.core
import django.core.serializers
import django.test

import ezidapp.models.update_queue

log = logging.getLogger(__name__)

def test_1000():
    """Test Django ORM model serialization"""
    q = ezidapp.models.update_queue.UpdateQueue.objects.all().order_by("seq")
    for o in q:
        print(o.cm)

    django.core.serializers.serialize('json', q)
