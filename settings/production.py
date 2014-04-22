from common import *

DEPLOYMENT_LEVEL = "production"

DEBUG = False

SEND_BROKEN_LINK_EMAILS = False

ALLOWED_HOSTS = ["ezid.cdlib.org", "ezid.lib.purdue.edu"]
LOCALIZATIONS["ezid.lib.purdue.edu"] = ("purdue", ["datacite@purdue.edu"])
# When the time comes, fill out and uncomment to enable the JISC localization:
# LOCALIZATIONS[?] = ("jisc-edina", ["edina@ed.ac.uk"])
