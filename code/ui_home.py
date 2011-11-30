from django.shortcuts import render_to_response
from django.template import Template,Context
import django.conf
import django.contrib.messages
import django.http
import django.template
import django.template.loader
import errno
import os
import re
import time
import urllib

import config
import datacite
import ezid
import ezidadmin
import idmap
import log
import metadata
import policy
import useradmin
import userauth

def home(request):
  test_list=['item 1','item 2','third time lucky']
  return render_to_response('home/home.html', {'test_list': test_list})
