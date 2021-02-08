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

import ezidapp.models.registration_queue


class DataciteQueue(ezidapp.models.registration_queue.RegistrationQueue):
    pass
