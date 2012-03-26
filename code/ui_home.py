from django.shortcuts import render_to_response
from django.conf import settings
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
  return uic.render(request, 'home/index', d)

def community(request):
  d = { 'menu_item' : 'ui_home.community' } 
  return uic.render(request, 'home/community', d)

def documentation(request):
  d = { 'menu_item' : 'ui_home.documentation' }
  return uic.render(request, 'home/documentation', d)

def outreach(request):
  d = { 'menu_item' : 'ui_home.outreach' }
  return uic.render(request, 'home/outreach', d)

def pricing(request):
  d = { 'menu_item' : 'ui_home.pricing' }
  return uic.render(request, 'home/pricing', d)

def understanding(request):
  d = { 'menu_item' : 'ui_home.understanding' }
  return uic.render(request, 'home/understanding', d)

def why(request):
  d = { 'menu_item' : 'ui_home.why' }
  return uic.render(request, 'home/why', d)

def contact(request):
  d = { 'menu_item' : 'null.null' }
  return uic.render(request, 'home/contact', d)