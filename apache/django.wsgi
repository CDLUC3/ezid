import os.path
import sys
sys.path.append(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0])

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
