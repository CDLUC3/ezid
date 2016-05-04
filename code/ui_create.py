import ui_common as uic
from django.shortcuts import redirect
import django.contrib.messages
import metadata
import ezid
import ezidapp.models
import urllib
import re
import datacite_xml
import os.path
from lxml import etree, objectify
import userauth

def index(request):
  d = { 'menu_item' : 'ui_create.index'}
  return redirect("ui_create.simple")

@uic.user_login_required
def simple(request):
  d = { 'menu_item' : 'ui_create.simple' }
  d["testPrefixes"] = uic.testPrefixes
  user = userauth.getUser(request)
  if user.isSuperuser:
    shoulders = [s for s in ezidapp.models.getAllShoulders() if not s.isTest]
  else:
    shoulders = user.shoulders.all()
  d["prefixes"] = sorted([{ "namespace": s.name, "prefix": s.prefix } for\
    s in shoulders],
    key=lambda p: ("%s %s" % (p["namespace"], p["prefix"])).lower())
  if len(d['prefixes']) < 1:
    return uic.render(request, 'create/no_shoulders', d)
  r = simple_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(r.split()[1], ":/"))
  else:
    return uic.render(request, 'create/simple', d)

@uic.user_login_required
def advanced(request):
  d = { 'menu_item' :'ui_create.advanced' }
  d["testPrefixes"] = uic.testPrefixes
  user = userauth.getUser(request)
  if user.isSuperuser:
    shoulders = [s for s in ezidapp.models.getAllShoulders() if not s.isTest]
  else:
    shoulders = user.shoulders.all()
  d["prefixes"] = sorted([{ "namespace": s.name, "prefix": s.prefix } for\
    s in shoulders],
    key=lambda p: ("%s %s" % (p["namespace"], p["prefix"])).lower())
  if len(d['prefixes']) < 1:
    return uic.render(request, 'create/no_shoulders', d)
  r = advanced_form_processing(request, d)
  if r == 'bad_request':
    uic.badRequest()
  elif r.startswith('created_identifier:'):
    return redirect("/id/" + urllib.quote(r.split()[1], ":/"))
  else:
    return uic.render(request, 'create/advanced', d)

def simple_form_processing(request, d):
  """ common code so that create simple identifier code does not repeat across real and test areas.
  returns either 'bad_request', 'edit_page' or 'created_identifier: <new_id>' for results """

  #selects current_profile based on parameters or profile preferred for prefix type
  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
  if 'current_profile' in REQUEST:
    d['current_profile'] = metadata.getProfile(REQUEST['current_profile'])
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
      s = ezid.mintIdentifier(request.POST['shoulder'],
        userauth.getUser(request, returnAnonymous=True),
        uic.assembleUpdateDictionary(request, d['current_profile'],
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
  choice_is_doi = False 
  if request.method == "GET":
    REQUEST = request.GET
  else:
    REQUEST = request.POST
  if (('shoulder' in REQUEST and REQUEST['shoulder'].startswith("doi:")) \
    or (len(d['prefixes']) > 0 and d['prefixes'][0]['prefix'].startswith('doi:'))):
      choice_is_doi = True 
  if 'current_profile' in REQUEST:
    if REQUEST['current_profile'] in uic.manual_profiles:
      d = _engage_datacite_xml_profile(request, d, REQUEST['current_profile'])
    else: 
      d['current_profile'] = metadata.getProfile(REQUEST['current_profile'])
      if d['current_profile'] == None:
        d['current_profile'] = metadata.getProfile('erc')
  else:
    if len(d['prefixes']) > 0 and d['prefixes'][0]['prefix'].startswith('doi:'):
      d = _engage_datacite_xml_profile(request, d, 'datacite_xml')
    else:
      d['current_profile'] = metadata.getProfile('erc')
  if d['manual_profile'] == False:
    d['current_profile_name'] = d['current_profile'].name
  d['internal_profile'] = metadata.getProfile('internal')
  d['profiles'] = [p for p in metadata.getProfiles()[1:] if p.editable]
  profs = [(p.name, p.displayName, ) for p in d['profiles']] + uic.manual_profiles.items()
  d['profile_names'] = sorted(profs, key=lambda p: p[1].lower())
  # 'datacite_xml' used for advanced profile instead of 'datacite'
  d['profile_names'].remove(('datacite','DataCite'))
  # [TODO: Enhance advanced DOI ERC profile to allow for elements ERC + datacite.publisher or 
  #    ERC + dc.publisher.] For now, just hide this profile. 
  if choice_is_doi: 
    d['profile_names'].remove(('erc','ERC'))
 
  if request.method == "POST":
    if "current_profile" not in request.POST or "shoulder" not in request.POST: return 'bad_request'
    pre_list = [p['prefix'] for p in d['prefixes']]
    if request.POST['shoulder'] not in pre_list:
      django.contrib.messages.error(request, "Unauthorized to create with this identifier prefix.")
      return 'edit_page'
    if uic.validate_advanced_metadata_form(request, d['current_profile']):
      """ # For advanced DOI's, this is handled via _datacite_xml.html
            template by ui_create.ajax_advanced
          No more manual profiles here for processing.
      """
      to_write = uic.assembleUpdateDictionary(request, d['current_profile'],
        { '_target' : uic.fix_target(request.POST['_target']),
        "_status": ("public" if request.POST["publish"] == "True" else "reserved"),
        "_export": ("yes" if request.POST["export"] == "yes" else "no") } )
      
      #write out ID and metadata (one variation with special remainder, one without)
      if request.POST['remainder'] == '' or request.POST['remainder'] == uic.remainder_box_default:
        s = ezid.mintIdentifier(request.POST['shoulder'],
          userauth.getUser(request, returnAnonymous=True), to_write)
      else:
        s = ezid.createIdentifier(request.POST['shoulder'] + request.POST['remainder'],
          userauth.getUser(request, returnAnonymous=True), to_write)
      if s.startswith("success:"):
        new_id = s.split()[1]
        django.contrib.messages.success(request, "Identifier created.")
        return 'created_identifier: ' + new_id
      else:
        if "-" in s:
          err_msg = re.search(r'^error: .+?- (.+)$', s).group(1)
        else:
          err_msg = re.search(r'^error: (.+)$', s).group(1)
        django.contrib.messages.error(request, "There was an error creating your identifier: "  + err_msg)
        return 'edit_page'
  return 'edit_page'

def _engage_datacite_xml_profile(request, d, profile_name):
  d['manual_profile'] = True
  d['current_profile_name'] = profile_name
  ''' Feed in a whole, empty XML record so that elements can be properly
      displayed in form fields on manage/edit page ''' 
  f = open(os.path.join(
    django.conf.settings.PROJECT_ROOT, "static", "datacite_emptyRecord.xml"))
  obj = objectify.parse(f).getroot()
  f.close()
  if obj is not None:
    d['datacite_obj'] = obj
  else:
    django.contrib.messages.error(request, "Unable to render empty datacite form using "\
      "file: " + f.name)
  d['manual_template'] = 'create/_' + d['current_profile_name'] + '.html'
  d['current_profile'] = d['current_profile_name']
  return d

def ajax_advanced(request):
  """Takes the request and processes create datacite advanced (xml) form
  from both create/demo and edit areas"""
  if request.is_ajax():
    d = {}
    error_msgs = []
    if (request.POST['action'] == 'create'):
      required = ['shoulder', 'remainder', '_target', 'publish', 'export']
      action_result = ['creating', 'created']
    else:   # action='edit'
      required = ['_target', '_export']
      action_result = ['editing', 'edited successfully']
      if not request.POST['identifier']:
        error_msgs.append("Unable to edit. Identifier not supplied.")
    d["testPrefixes"] = uic.testPrefixes
    user = userauth.getUser(request, returnAnonymous=True)
    if user.isSuperuser:
      shoulders = [s for s in ezidapp.models.getAllShoulders() if not s.isTest]
    else:
      shoulders = user.shoulders.all()
    d["prefixes"] = sorted([{ "namespace": s.name, "prefix": s.prefix } for\
      s in shoulders],
      key=lambda p: ("%s %s" % (p["namespace"], p["prefix"])).lower())
    pre_list = [p['prefix'] for p in d['prefixes'] + d['testPrefixes']]
    if (request.POST['action'] == 'create' and\
        request.POST['shoulder'] not in pre_list):
        error_msgs.append("Unauthorized to create with this identifier prefix.")
    for x in required:
      if x not in request.POST:
        error_msgs.append("A required form element was not submitted.")
        return uic.jsonResponse({'status': 'failure', 'errors': error_msgs })

    error_msgs = error_msgs + uic.validate_advanced_top(request)
    for k, v in {'/resource/creators/creator[1]/creatorName': 'creator name',
                 '/resource/titles/title[1]': 'title',
                 '/resource/publisher': 'publisher',
                 '/resource/publicationYear': 'publication year'}.items():
      if (not (k in request.POST)) or request.POST[k].strip() == '':
        error_msgs.append("Please enter a " + v)
    
    if ('/resource/publicationYear' in request.POST) and \
              not re.compile('^\d{4}$').match(request.POST['/resource/publicationYear']):
      error_msgs.append("Please enter a four digit year for the publication year.")
      
    #for k, v in request.POST.iteritems():
    #  if v:
    #    if re.match(r'^/resource/dates/date\[\d+?\]$', k ) and not re.match(r'^\d{4}', v ):
    #      error_msgs.append("Please ensure your date is numeric and in the correct format.")
    if len(error_msgs) > 0:
      return uic.jsonResponse({'status': 'failure', 'errors': error_msgs })

    return_val = datacite_xml.generate_xml(request.POST)
    xsd_path = django.conf.settings.PROJECT_ROOT + "/xsd/datacite-kernel-3/metadata.xsd"
    if datacite_xml.validate_document(return_val, xsd_path, error_msgs) == False:
      return uic.jsonResponse({'status': 'failure', 'errors': error_msgs })

    if (request.POST['action'] == 'edit'): 
      if request.POST['_status'] == 'unavailable':
        stts = request.POST['_status'] + " | " + request.POST['stat_reason']
      else:
        stts = request.POST['_status']
      to_write = _assembleMetadata(request, stts, return_val) 
      s = ezid.setMetadata(request.POST['identifier'],
        userauth.getUser(request, returnAnonymous=True), to_write)
    else:  # action=='create'
      stts = ("public" if request.POST["publish"] == "True" else "reserved")
      to_write = _assembleMetadata(request, stts, return_val) 
      
      #write out ID and metadata (one variation with special remainder, one without)
      if request.POST['remainder'] == '' or\
         request.POST['remainder'] == uic.remainder_box_default:
        s = ezid.mintIdentifier(request.POST['shoulder'],
          userauth.getUser(request, returnAnonymous=True), to_write)
      else:
        s = ezid.createIdentifier(request.POST['shoulder'] +\
          request.POST['remainder'],
          userauth.getUser(request, returnAnonymous=True), to_write)

    if s.startswith("success:"):
      new_id = s.split()[1]
      django.contrib.messages.success(request, "Identifier " + action_result[1] + ".")
      return uic.jsonResponse({'status': 'success', 'id': new_id })
    else:
      return uic.jsonResponse({'status': 'failure', 'errors': ["There was an error " +
        action_result[0] + " your identifier:"  + s] })
 
def _assembleMetadata (request, stts, return_val):
    # There is no datacite_xml ezid profile. Just use 'datacite'
    return { "_profile": 'datacite',
      '_target' : uic.fix_target(request.POST['_target']),
      "_status": stts,
      "_export": ("yes" if request.POST.get("export", "no") == "yes" or
                  request.POST.get("_export", "no") == "yes" else "no"),
      "datacite": return_val }
 
