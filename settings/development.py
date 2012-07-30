from common import *

DEPLOYMENT_LEVEL = "development"

#This tells a special template tag to substitute
#one template for another if the host name is in this dictionary
HOST_TEMPLATE_CUSTOMIZATION = {'n2t-dev-alt.cdlib.org': 'purdue'}

#tells contact-us mailer to mail to different address if domain in this dictionary
HOST_EMAIL_CUSTOMIZATION = {'n2t-dev-alt.cdlib.org': 'scott.fisher@ucop.edu'}
