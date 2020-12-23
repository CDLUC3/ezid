# =============================================================================
#
# EZID :: ezidapp/models/datacite_queue.py
#
# Database model for the DataCite queue.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

from . import registration_queue


class DataciteQueue(registration_queue.RegistrationQueue):
    pass
