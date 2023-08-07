#  Copyright©2023, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Object Relational Mapper (ORM) models for the minters
"""
import time
import logging

import django.db.models
import django.core.serializers.json
import django.core.validators
from ezidapp.models  import validation
import impl.util

logger = logging.getLogger(__name__)

def default_time():
    return int(time.time())

class Minter(django.db.models.Model):
    # Class for the Minters. 
    # Minters are uniquely identified by a prefix/shoulder;
    # Each minter maintains its own state which is stored in the minterState field.

    # The shoulder itself, qualified and normalized, e.g., "ark:/12345/"
    # or "doi:10.1234/FOO".
    prefix = django.db.models.CharField(
        max_length=impl.util.maxIdentifierLength,
        unique=True,
        validators=[validation.shoulder],
    )

    # minter state in JSON
    minterState = django.db.models.JSONField(
        encoder=django.core.serializers.json.DjangoJSONEncoder,
        default=dict,
    )
    
    # The time the identifier was created as a Unix timestamp. If not
    # specified, the current time is used.
    createTime = django.db.models.IntegerField(
        default=default_time(),
        validators=[django.core.validators.MinValueValidator(0)],
        db_index=True,
    )

    # The time the minter was last updated as a Unix timestamp. If
    # not specified, the current time is used.
    updateTime = django.db.models.IntegerField(
        default=default_time(),
        validators=[django.core.validators.MinValueValidator(0)],
        db_index=True,
    )
    
    def __str__(self):
        return (
            f'{self.__class__.__name__}('
            f'prefix={self.prefix}, '
            f'minterState={self.minterState}'
            f')'
        )
    






