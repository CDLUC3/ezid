from django.shortcuts import render_to_response
from django.conf import settings
from django.template import loader
import datetime
import ui_common as uic
import feedparser

feed_cache = () #time cache expires, title, link

def index(request):
  d = { 'menu_item' : 'ui_home.index'}
  global feed_cache
  try:
    if len(feed_cache) == 0 or datetime.datetime.now() > feed_cache[0]:
      fd = feedparser.parse(settings.RSS_FEED)
      feed_cache = (datetime.datetime.now() + datetime.timedelta(0, 60*60), \
                    fd.entries[0].title, fd.entries[0].link)
  except:
    feed_cache = (datetime.datetime.now() + datetime.timedelta(0, 10*60), \
                    'RSS Feed Unavailable', settings.RSS_FEED)
  d['feed_cache'] = feed_cache
  d['rss_feed'] = settings.RSS_FEED
  d['ezid_home_url'] = "http://" + request.get_host() +"/ezid/"
  return uic.render(request, 'info/index', d)

def community(request):
  d = { 'menu_item' : 'ui_home.community' } 
  return uic.render(request, 'info/community', d)

def documentation(request):
  d = { 'menu_item' : 'ui_home.documentation' }
  return uic.render(request, 'info/documentation', d)

def outreach(request):
  d = { 'menu_item' : 'ui_home.outreach' }
  return uic.render(request, 'info/outreach', d)

def pricing(request):
  d = { 'menu_item' : 'ui_home.pricing' }
  return uic.render(request, 'info/pricing', d)

def understanding(request):
  d = { 'menu_item' : 'ui_home.understanding' }
  return uic.render(request, 'info/understanding', d)

def why(request):
  d = { 'menu_item' : 'ui_home.why' }
  return uic.render(request, 'info/why', d)

def no_menu(request, template_name):
  d = {'menu_item' : 'ui_home.null'}
  try:
    loader.get_template('info/' + template_name + ".html")
  except:
    return uic.error(404)
  return uic.render(request, 'info/' + template_name, d)

