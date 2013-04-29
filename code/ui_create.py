import ui_common as uic
from django.shortcuts import redirect
import django.contrib.messages
import metadata
import ezid
import logging
import urllib
import re
from lxml import etree

def index(request):
  d = { 'menu_item' : 'ui_create.index'}
  return redirect("ui_create.simple")

@uic.user_login_required
def simple(request):
  d = { 'menu_item' : 'ui_create.simple' }
  d["testPrefixes"] = uic.testPrefixes
  d['prefixes'] = sorted(request.session['prefixes'], key=lambda p: p['namespace'].lower()) #must be done before calling form processing
  if len(d['prefixes']) < 1:
    return uic.render(request, 'create/no_shoulders', d)
  r = simple_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("/ezid/id/" + urllib.quote(r.split()[1], ":/"))
  else:
    return uic.render(request, 'create/simple', d)

@uic.user_login_required
def advanced(request):
  d = { 'menu_item' :'ui_create.advanced' }
  d["testPrefixes"] = uic.testPrefixes
  d['prefixes'] = sorted(request.session['prefixes'], key=lambda p: p['namespace'].lower()) #must be done before calling form processing
  if len(d['prefixes']) < 1:
    return uic.render(request, 'create/no_shoulders', d)
  r = advanced_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("/ezid/id/" + urllib.quote(r.split()[1], ":/"))
  else:
    return uic.render(request, 'create/advanced', d)

def simple_form_processing(request, d):
  """ common code so that create simple identifier code does not repeat across real and test areas.
  returns either 'bad_request', 'edit_page' or 'created_identifier: <new_id>' for results """

  #selects current_profile based on parameters or profile preferred for prefix type
  if 'current_profile' in request.REQUEST:
    d['current_profile'] = metadata.getProfile(request.REQUEST['current_profile'])
    if d['current_profile'] == None:
      d['current_profile'] = metadata.getProfile('erc')
  else:
    if len(d['prefixes']) > 0 and d['prefixes'][0]['prefix'].startswith('doi:'):
      d['current_profile'] = metadata.getProfile('datacite')
    else:
      d['current_profile'] = metadata.getProfile('erc')
      
  d['internal_profile'] = metadata.getProfile('internal')
  
  if request.method == "POST":
    if "current_profile" not in request.POST or "shoulder" not in request.POST: return "bad_request"
    pre_list = [p['prefix'] for p in d['prefixes']]
    if request.POST['shoulder'] not in pre_list:
      django.contrib.messages.error(request, "Unauthorized to create with this identifier prefix.")
      return "edit_page"
    
    if uic.validate_simple_metadata_form(request, d['current_profile']):
      s = ezid.mintIdentifier(request.POST['shoulder'], uic.user_or_anon_tup(request),
          uic.group_or_anon_tup(request), uic.assembleUpdateDictionary(request, d['current_profile'],
          { '_target' : uic.fix_target(request.POST['_target']),
           '_export': 'yes' }))
      if s.startswith("success:"):
        new_id = s.split()[1]
        django.contrib.messages.success(request, "Identifier created.")
        return "created_identifier: "+new_id
      else:
        django.contrib.messages.error(request, "There was an error creating your identifier:"  + s)
        return "edit_page"
  return 'edit_page'

def advanced_form_processing(request, d):
  """takes request and context object, d['prefixes'] should be set before calling"""
  #sets manual_profile, current_profile, current_profile_name, internal_profile,
  #     profiles, profile_names
  
  #Form set up
  d['remainder_box_default'] = uic.remainder_box_default
  #selects current_profile based on parameters or profile preferred for prefix type
  d['manual_profile'] = False
  if 'current_profile' in request.REQUEST:
    if request.REQUEST['current_profile'] in uic.manual_profiles:
      d['manual_profile'] = True
      d['current_profile_name'] = request.REQUEST['current_profile']
      d['manual_template'] = 'create/_' + d['current_profile_name'] + '.html'
      d['current_profile'] = d['current_profile_name']
    else: 
      d['current_profile'] = metadata.getProfile(request.REQUEST['current_profile'])
      if d['current_profile'] == None:
        d['current_profile'] = metadata.getProfile('erc')
  else:
    if len(d['prefixes']) > 0 and d['prefixes'][0]['prefix'].startswith('doi:'):
      d['current_profile'] = metadata.getProfile('datacite')
    else:
      d['current_profile'] = metadata.getProfile('erc')
  if d['manual_profile'] == False:
    d['current_profile_name'] = d['current_profile'].name
  d['internal_profile'] = metadata.getProfile('internal')
  d['profiles'] = metadata.getProfiles()[1:]
  profs = [(p.name, p.displayName, ) for p in d['profiles']] + uic.manual_profiles.items()
  d['profile_names'] = sorted(profs, key=lambda p: p[1].lower())
  
  
  if request.method == "POST":
    if "current_profile" not in request.POST or "shoulder" not in request.POST: return 'bad_request'
    pre_list = [p['prefix'] for p in d['prefixes']]
    if request.POST['shoulder'] not in pre_list:
      django.contrib.messages.error(request, "Unauthorized to create with this identifier prefix.")
      return 'edit_page'
    if uic.validate_advanced_metadata_form(request, d['current_profile'], d['manual_profile']):
      if d['manual_profile']:
        methods = {'datacite_xml': _generate_datacite_xml}
        return_val = methods[d['current_profile_name']](request)
        #do something to process this manual profile
        #then write it to EZID somehow
        return 'edit_page' #this just terminates early for now, so garbage doesn't go in yet
      else:
        to_write = uic.assembleUpdateDictionary(request, d['current_profile'],
          { '_target' : uic.fix_target(request.POST['_target']),
          "_status": ("public" if request.POST["publish"] == "True" else "reserved"),
          "_export": ("yes" if request.POST["export"] == "yes" else "no") } )
      
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
        return 'created_identifier: ' + new_id
      else:
        django.contrib.messages.error(request, "There was an error creating your identifier:"  + s)
        return 'edit_page'
  return 'edit_page'

def _generate_datacite_xml(request):
  """This generates datacite XML from a form POST request and returns it"""
  r = etree.fromstring('<resource xmlns="http://datacite.org/schema/kernel-2.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://datacite.org/schema/kernel-2.2 http://schema.datacite.org/meta/kernel-2.2/metadata.xsd"/>')

  items = request.POST.items()
  items = [x for x in items if x[0].startswith("/resource") ]
  RESOURCE_ORDER = ["/resource/" + x for x in ['creators', 'titles', 'publisher', 'publicationYear', 'subjects', 
                    'contributors', 'dates', 'language', 'resourceType', 'alternateIdentifiers',
                    'relatedIdentifiers', 'rights', 'descriptions'] ]
  items = sorted(items, key=lambda i: i[0]) #sort by element name
  #sort by first ordinal in string, will cause problems if schema gets complex enough to have more than one ordinal per xpath
  items = sorted(items, key=lambda i: _sort_get_ordinal(i[0]))
  #items = sorted(items, key=lambda i: len(i[0].split("/"))) #sort by element length
  items = sorted(items, key=lambda i: RESOURCE_ORDER.
                 index(re.search('^/resource/[a-zA-Z0-9\[\]]+', i[0]).group())) #sort in preferred order of sections

  for k, v in items:
    if v != '':
      _create_xml_element(r, k, v)
      print k + "=" + v
      #print etree.tostring(r, pretty_print=True)
      #print ''
    
  print etree.tostring(r, pretty_print=True)
  return ''

def _create_xml_element(root_el, path, value):
  """ creates xml element """
  split_path = path.split("/")[1:]
  if split_path[0] == _remove_ns(root_el.tag):
    split_path = split_path[1:]
  _xml_create(root_el, split_path, value)
  
def _xml_create(base_el, path_arr, value):
  #create or check element here
  tag = path_arr[0]
  simple_tag = _remove_at(_remove_ordinal(tag))
  children = _children_w_tag(base_el, simple_tag)
  if _is_attribute(tag):
    #set an attribute
    if len(path_arr) > 1:
      #this shouldn't happen
      return
    else:
      base_el.set(simple_tag, value)
  else:
    if _has_ordinal(tag):
      ord = _get_ordinal(tag) - 1 #must subtract one because form ordinals start at 1, not 0
    else:
      ord = 0  #no ordinal, then it's effectively an ordinal of the first [0]
    if ord > len(children) - 1:
      child = etree.Element(simple_tag)
      base_el.append(child)
    else:
      child = children[ord]
    if len(path_arr) == 1:
      child.text = value  #leaf node, so set value
    else:
      _xml_create(child, path_arr[1:], value) #not leaf node, so recurse for more path

def _remove_ns(str):
  """ removes the horrifying namespace uri from string so can compare easily"""
  return re.sub(r'^{[^}]+}', '', str)

def _children_w_tag(base, tag):
  return [ child for child in base.iter(tag) ]
  #was [child for child in base if _remove_ns(child.tag) == tag ]

def _remove_ordinal(str):
  """removes the ordinal like [1] from path element"""
  return re.sub(r'\[[0-9]+\]$', '', str)

def _has_ordinal(str):
  """sees if it has an ordinal like [1] at end of element"""
  return str.endswith("]")

def _get_ordinal(str):
  """gets the ordinal at end of element string like [1] and returns an integer"""
  return int(re.search('\[([0-9]+)\]$', str).group(1))

def _is_attribute(str):
  """sees if this element string is an attribute"""
  return str.startswith("@")

def _remove_at(str):
  """removes an @ sign at beginning of string if it exists"""
  return re.sub(r'^@', '', str)

def _sort_get_ordinal(str):
  """gets the ordinal at end of element string, if it doesn't have one return 0"""
  m = re.compile('\[([0-9]+)\]')
  if m.search(str) == None:
    return 0
  else:
    return int(m.search(str).group(1))