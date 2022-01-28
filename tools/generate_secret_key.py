#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Generate a random string for use in the Django SECRET_KEY setting
"""

import random

_secretKeyLength = 50


def generate_secret_key():
    rng = random.SystemRandom()
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"
    key = "".join(rng.choice(alphabet) for _ in range(_secretKeyLength))
    print(key)


generate_secret_key()
