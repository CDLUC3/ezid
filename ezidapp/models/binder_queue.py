# =============================================================================
#
# EZID :: ezidapp/models/binder_queue.py
#
# Database model for the N2T binder queue.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

from . import registration_queue


class BinderQueue(registration_queue.RegistrationQueue):
    pass
