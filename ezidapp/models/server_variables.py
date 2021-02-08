# =============================================================================
#
# EZID :: ezidapp/models/server_variables.py
#
# Storage of runtime server variables in the store database.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import logging
import random

import django.db.models

_secretKeyLength = 50


logger = logging.getLogger(__name__)


class ServerVariables(django.db.models.Model):
    # This is a one-row pseudo-table that stores server variables.

    alertMessage = django.db.models.CharField(
        "alert message",
        max_length=255,
        blank=True,
        help_text="The alert message can be used to communicate "
        + "urgent announcements.  It is displayed at the top of every UI page.",
    )
    # The system alert message.

    secretKey = django.db.models.CharField(
        "secret key",
        max_length=_secretKeyLength,
        blank=True,
        help_text="The secret key identifies the server; "
        + "changing it invalidates every API session cookie, password reset URL, "
        + "and OAI-PMH resumption token.  Set it to blank to generate a new "
        + "random key.",
    )
    # Stored value of django.conf.settings.SECRET_KEY.

    def clean(self):
        self.alertMessage = self.alertMessage.strip()

    def __str__(self):
        return "Row 1"

    class Meta:
        verbose_name_plural = "server variables"


def getAlertMessage():
    return ServerVariables.objects.get(id=1).alertMessage


def setAlertMessage(s):
    ServerVariables.objects.filter(id=1).update(alertMessage=s.strip())


def getOrSetSecretKey():
    # Returns the stored value of django.conf.settings.SECRET_KEY.  If
    # there is no stored value, a new key is generated and stored (and
    # returned).
    # try:
    row = ServerVariables.objects.get(id=1)

    while row.secretKey == "":
        logger.debug('Current SECRET_KEY is empty. Generating new')
        rng = random.SystemRandom()
        alphabet = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
        key = "".join(rng.choice(alphabet) for _ in range(_secretKeyLength))
        # We go to some effort to avoid race conditions.  We set the key
        # only if it hasn't been set, then ask for the value back.
        ServerVariables.objects.filter(secretKey="").update(secretKey=key)
        row = ServerVariables.objects.get(id=1)
    return row.secretKey
