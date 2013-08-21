import ui_common as uic
from django.shortcuts import redirect
import django.contrib.messages
import metadata
import ezid
import ui_create
import urllib
import datacite_xml
import os
from lxml import etree
def index(request):
  d = { 'menu_item' : 'ui_demo.index' }
  return redirect("ui_demo.simple")
  return uic.render(request, 'create/index', d)

def simple(request):
  d = { 'menu_item' :'ui_demo.simple' }
  d["testPrefixes"] = uic.testPrefixes
  d['prefixes'] = sorted(uic.testPrefixes, key=lambda p: p['namespace'].lower()) #must be done before calliung form processing
  r = ui_create.simple_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("/ezid/id/" + urllib.quote(r.split()[1], ":/"))
  else:
    return uic.render(request, 'demo/simple', d)

def advanced(request):
  d = { 'menu_item' : 'ui_demo.advanced' }
  d["testPrefixes"] = uic.testPrefixes
  d['prefixes'] = sorted(uic.testPrefixes, key=lambda p: p['namespace'].lower()) #must be done before calling form processing
  r = ui_create.advanced_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("/ezid/id/" + urllib.quote(r.split()[1], ":/"))
  else:
    return uic.render(request, 'demo/advanced', d)
  
def ajax_advanced(request):
  """Takes the request and processes create datacite advanced (xml) form
  from both create/demo areas"""
  if request.is_ajax():
    d = {}
    error_msgs = []
    d["testPrefixes"] = uic.testPrefixes
    if 'prefixes' in request.session:
      d['prefixes'] = sorted(request.session['prefixes'], key=lambda p: p['namespace'].lower())
    else:
      d['prefixes'] = []
    pre_list = [p['prefix'] for p in d['prefixes'] + d['testPrefixes']]
    if request.POST['shoulder'] not in pre_list:
      error_msgs.append("Unauthorized to create with this identifier prefix.")
    error_msgs = error_msgs + uic.validate_advanced_top(request)
    for k, v in {'/resource/creators/creator[1]/creatorName': 'creator name',
                 '/resource/titles/title[1]': 'title',
                 '/resource/publisher': 'publisher',
                 '/resource/publicationYear': 'publication year'}.items():
      if (not (k in request.POST)) or request.POST[k].strip() == '':
        error_msgs.append("Please enter a " + v)
    
    if len(error_msgs) > 0:
      return uic.jsonResponse({'status': 'failure', 'errors': error_msgs })
    
    return_val = datacite_xml.generate_xml(request.POST)
    
    # *** validate against XSD ***
    cleansed_xml = return_val.replace('encoding="UTF-8"', '', 1)
    xsd_doc = etree.parse(django.conf.settings.PROJECT_ROOT + \
                           "/xsd/datacite3-kernel/metadata.xsd")
    xsd = etree.XMLSchema(xsd_doc)
    parser = etree.XMLParser(ns_clean=True, recover=True)
    xml = etree.fromstring(cleansed_xml, parser)
    
    # must add something like <identifier identifierType="DOI">10.5072/FK25Q56C6</identifier>
    # because it will not validate until it's present, even though we haven't minted
    # an identifier yet, but want to validate as though we had
    el = xml.find('{http://datacite.org/schema/kernel-3}identifier')
    el.attrib['identifierType'] = 'DOI'
    el.text = '10.5072/FK25Q56C6'
    
    if not xsd.validate(xml):
      error_msgs.append("XML validation errors occurred for the values you entered:")
      for x in [x.message for x in xsd.error_log]:
        error_msgs.append(x)
      return uic.jsonResponse({'status': 'failure', 'errors': error_msgs })
    # *** end validate against XSD ***

    #print return_val #for debugging
    to_write = \
    { "_profile": "datacite", 
      '_target' : uic.fix_target(request.POST['_target']),
      "_status": ("public" if request.POST["publish"] == "True" else "reserved"),
      "_export": ("yes" if request.POST["export"] == "yes" else "no"),
      "datacite": return_val }
      
    #write out ID and metadata (one variation with special remainder, one without)
    if request.POST['remainder'] == '' or request.POST['remainder'] == uic.remainder_box_default:
      s = ezid.mintIdentifier(request.POST['shoulder'], uic.user_or_anon_tup(request), 
          uic.group_or_anon_tup(request), to_write)
    else:
      s = ezid.createIdentifier(request.POST['shoulder'] + request.POST['remainder'], uic.user_or_anon_tup(request),
        uic.group_or_anon_tup(request), to_write)
    if s.startswith("success:"):
      new_id = s.split()[1]
      django.contrib.messages.success(request, "Identifier created.")
      return uic.jsonResponse({'status': 'success', 'id': new_id })
    else:
      return uic.jsonResponse({'status': 'failure', 'errors': ["There was an error creating your identifier:"  + s] })
  