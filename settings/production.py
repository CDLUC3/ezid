from common import *

DEPLOYMENT_LEVEL = "production"

DEBUG = False

SEND_BROKEN_LINK_EMAILS = False

#This tells a special template tag to substitute
#one template for another if the host name is in this dictionary
HOST_TEMPLATE_CUSTOMIZATION = {'ezid.lib.purdue.edu': 'purdue'}

#tells contact-us mailer to mail to different address if domain in this dictionary
HOST_EMAIL_CUSTOMIZATION = {'ezid.lib.purdue.edu': 'datacite@purdue.edu'}
