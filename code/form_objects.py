from django import forms
from django.forms import BaseFormSet, formset_factory
import django.core.validators
import util
import idmap
import userauth 
import re
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

""" Django form framework added in 2016 release of EZID UI.
    Bulk of form validation occurs here. Avoiding JavaScript form validation
    in most cases in the UI.
"""

#### Constants ####

REMAINDER_BOX_DEFAULT = _("Recommended: Leave blank")
RESOURCE_TYPES = (
  ('', _("Select a type of object")), ('Audiovisual', _('Audiovisual')), 
  ('Collection', _('Collection')), ('Dataset', _('Dataset')), 
  ('Event', _('Event')), ('Image', _('Image')), 
  ('InteractiveResource', _('InteractiveResource')), ('Model', _('Model')), 
  ('PhysicalObject', _('PhysicalObject')), ('Service', _('Service')), 
  ('Software', _('Software')), ('Sound', _('Sound')), ('Text', _('Text')), 
  ('Workflow', _('Workflow')), ('Other', _('Other'))
)
REGEX_4DIGITYEAR='^(\d{4}|\(:unac\)|\(:unal\)|\(:unap\)|\(:unas\)|\(:unav\)|\
   \(:unkn\)|\(:none\)|\(:null\)|\(:tba\)|\(:etal\)|\(:at\))$'
ERR_4DIGITYEAR = _("4-digits")
ERR_CREATOR=_("Please fill in a value for creator.")
ERR_TITLE=_("Please fill in a value for title.")
ERR_PUBLISHER=_("Please fill in a value for publisher.")
PREFIX_CREATOR_SET='creators-creator'
PREFIX_TITLE_SET='titles-title'
PREFIX_DESCR_SET='descriptions-description'
PREFIX_SUBJECT_SET='subjects-subject'
PREFIX_CONTRIBUTOR_SET='contributors-contributor'
PREFIX_GEOLOC_SET='geoLocations-geoLocation'

################# Basic ID Forms ####################

class BaseForm(forms.Form):
  """ Base Form object: all forms have a target field. If 'placeholder' is True
      set attribute to include specified placeholder text in text fields """
  def __init__(self, *args, **kwargs):
    self.placeholder = kwargs.pop('placeholder',None)
    super(BaseForm,self).__init__(*args,**kwargs)
    self.fields["target"]=forms.CharField(required=False, label=_("Location (URL)"),
      validators=[_validate_url])
    if self.placeholder is not None and self.placeholder == True:
      self.fields['target'].widget.attrs['placeholder'] = _("Location (URL)")

class ErcForm(BaseForm):
  """ Form object for ID with ERC profile (Used for simple or advanced ARK).
      BaseForm parent brings in target field. If 'placeholder' is True 
      set attribute to include specified placeholder text in text fields """
  def __init__(self, *args, **kwargs):
    super(ErcForm,self).__init__(*args,**kwargs)
    self.fields["erc.who"]=forms.CharField(required=False, label=_("Who"))
    self.fields["erc.what"]=forms.CharField(required=False, label=_("What"))
    self.fields["erc.when"]=forms.CharField(required=False, label=_("When"))
    if self.placeholder is not None and self.placeholder == True:
      self.fields['erc.who'].widget.attrs['placeholder'] = _("Who?")
      self.fields['erc.what'].widget.attrs['placeholder'] = _("What?")
      self.fields['erc.when'].widget.attrs['placeholder'] = _("When?")

class DcForm(BaseForm):
  """ Form object for ID with Dublin Core profile (Advanced ARK or DOI).
      BaseForm parent brings in target field. If 'placeholder' is True set 
      attribute to include specified placeholder text in text fields """
  def __init__(self, *args, **kwargs):
    self.isDoi = kwargs.pop('isDoi',None)
    super(DcForm,self).__init__(*args,**kwargs)
    self.fields["dc.creator"] = forms.CharField(label=_("Creator"),
      required=True if self.isDoi else False)
    self.fields["dc.title"] = forms.CharField(label=_("Title"),
      required=True if self.isDoi else False)
    self.fields["dc.publisher"] = forms.CharField(label=_("Publisher"),
      required=True if self.isDoi else False)
    self.fields["dc.date"] = forms.CharField(label=_("Date"),
      required=True if self.isDoi else False)
    self.fields["dc.type"] = forms.CharField(required=False, label=_("Type"))

class DataciteForm(BaseForm):
  """ Form object for ID with (simple DOI) DataCite profile. BaseForm parent brings in 
      target field. If 'placeholder' is True set attribute to include specified
      placeholder text in text fields """
  def __init__(self, *args, **kwargs):
    super(DataciteForm,self).__init__(*args,**kwargs)
    self.fields["datacite.creator"] = forms.CharField(label=_("Creator"),
      error_messages={'required': ERR_CREATOR}) 
    self.fields["datacite.title"] = forms.CharField(label=_("Title"),
      error_messages={'required': ERR_TITLE})
    self.fields["datacite.publisher"] = forms.CharField(label=_("Publisher"),
      error_messages={'required': ERR_PUBLISHER})
    self.fields["datacite.publicationyear"] = forms.RegexField(label=_("Publication year"),
      regex=REGEX_4DIGITYEAR,
      error_messages={'required': _("Please fill in a value for publication year."),
                    'invalid': ERR_4DIGITYEAR })
    # Translators: These options appear in drop-down on ID Creation page (DOIs)
    self.fields["datacite.resourcetype"] = \
      forms.ChoiceField(required=False, choices=RESOURCE_TYPES, label=_("Resource type"))
    if self.placeholder is not None and self.placeholder == True:
      self.fields['datacite.creator'].widget.attrs['placeholder'] = _("Creator")
      self.fields['datacite.title'].widget.attrs['placeholder'] = _("Title")
      self.fields['datacite.publisher'].widget.attrs['placeholder'] = _("Publisher")
      self.fields['datacite.publicationyear'].widget.attrs['placeholder'] = _("Publication year")

def getIdForm (profile, placeholder, elements=None):
  """ Returns a simple ID Django form. If 'placeholder' is True
      set attribute to include specified placeholder text in text fields """
  # Django forms does not handle field names with underscores very well
  if elements and '_target' in elements: elements['target'] = elements['_target']
  if profile.name == 'erc': 
    form = ErcForm(elements, placeholder=placeholder, auto_id='%s')
  elif profile.name == 'datacite': 
    form = DataciteForm(elements, placeholder=placeholder, auto_id='%s')
  elif profile.name == 'dc': 
    testForDoi=None    # dc.creator is only required when creating a DOI
    form = DcForm(elements, placeholder=placeholder, isDoi=testForDoi, auto_id='%s')
  return form

################# Advanced ID Form Retrieval ###########################
### (two forms technically: RemainderForm and Profile Specific Form) ###

class RemainderForm(forms.Form):
  """ Remainder Form object: all advanced forms have a remainder field,
      validation of which requires passing in the shoulder """
  def __init__(self, *args, **kwargs):
    self.shoulder = kwargs.pop('shoulder',None)
    super(RemainderForm,self).__init__(*args,**kwargs)
    self.fields["remainder"]=forms.CharField(required=False, 
      label=_("Custom Remainder"), initial=REMAINDER_BOX_DEFAULT, 
      validators=[_validate_custom_remainder(self.shoulder)])

def getAdvancedIdForm (profile, request=None):
  """ For advanced ID (but not datacite_xml). Returns two forms: One w/a 
      single remainder field and one with profile-specific fields """
  P = shoulder = isDoi = None
  if request: 
    assert request.method == 'POST'
    P = request.POST
    shoulder=P['shoulder']
    isDoi = "True" if shoulder.startswith("doi:") else None
  remainder_form = RemainderForm(P, shoulder=shoulder, auto_id='%s')
  if profile.name == 'erc': form = ErcForm(P, auto_id='%s')
  elif profile.name == 'datacite': form = DataciteForm(P, auto_id='%s')
  elif profile.name == 'dc': form = DcForm(P, isDoi=isDoi, auto_id='%s')
  return {'remainder_form': remainder_form, 'form': form}

################# Form Validation functions  #################

def _validate_url(url):
  """ Borrowed from code/ezid.py """
  t = url.strip()
  if t != "":
    try:
      assert len(t) <= 2000
      django.core.validators.URLValidator()(t)
    except:
      raise ValidationError(_("Please enter a valid location (URL)"))

def _validate_custom_remainder(shoulder):
  def innerfn(remainder_to_test):
    test = "" if remainder_to_test == REMAINDER_BOX_DEFAULT \
      else remainder_to_test
    if not (util.validateIdentifier(shoulder + test)):
      raise ValidationError(
        _("This combination of characters cannot be used as a remainder."))
  return innerfn

def nameIdValidation(ni, ni_s, ni_s_uri):
  err = {}
  if ni and not ni_s:
    err['nameIdentifier-nameIdentifierScheme'] = _("An Identifier Scheme must be filled in if you specify an Identifier.")
  if ni_s and not ni:
    err['nameIdentifier'] = _("An Identifier must be filled in if you specify an Identifier Scheme.")
  if ni_s_uri:
    if not ni:
      err['nameIdentifier'] = _("An Identifier must be filled in if you specify a Scheme URI.")
    if not ni_s:
      err['nameIdentifier-nameIdentifierScheme'] = _("An Identifier Scheme must be filled in.")
  return err

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
################# Advanced Datacite ID Form/Elements #################

class NonRepeatingForm(forms.Form):
  """ Form object for single field elements in DataCite Advanced (XML) profile """
  target=forms.CharField(required=False, label=_("Location (URL)"),
    validators=[_validate_url])
  publisher = forms.CharField(label=_("Publisher"),
    error_messages={'required': ERR_PUBLISHER})
  publicationYear = forms.RegexField(label=_("Publication Year"),
    regex=REGEX_4DIGITYEAR,
    error_messages={'required': _("Please fill in a value for publication year."),
                    'invalid': ERR_4DIGITYEAR })
  language = forms.CharField(required=False, label=_("Language"))
  version = forms.CharField(required=False, label=_("Version"))

class ResourceTypeForm(forms.Form):
  """ This is also composed of single field elements like NonRepeatingForm,
      but I wasn't sure how to call fields with hyphens (from NonRepeatingForm)
      directly from the template.  By relegating them to their own form object, 
      this bypasses that problem. 
  """
  def __init__(self, *args, **kwargs):
    super(ResourceTypeForm,self).__init__(*args,**kwargs)
    self.fields['resourceType-resourceTypeGeneral'] = forms.ChoiceField(required=False,
      choices=RESOURCE_TYPES, initial='Dataset', label = _("Resource Type General"))
    self.fields['resourceType'] = forms.CharField(required=False, label=_("Resource Type"))

# Django faulty design: First formset allows blank form fields.
# http://stackoverflow.com/questions/2406537/django-formsets-make-first-required
class RequiredFormSet(BaseFormSet):
  """ Sets first form in a formset required. Used for TitleSet. """
  def __init__(self, *args, **kwargs):
    super(RequiredFormSet, self).__init__(*args, **kwargs)
    self.forms[0].empty_permitted = False

# Remaining Datacite Forms listed below are intended to be wrapped into FormSets (repeatable)
class CreatorForm(forms.Form):
  """ Form object for Creator Element in DataCite Advanced (XML) profile """
  def __init__(self, *args, **kwargs):
    super(CreatorForm,self).__init__(*args,**kwargs)
    self.fields["creatorName"] = forms.CharField(label=_("Name"),
      error_messages={'required': _("Please fill in a value for creator name.")})
    self.fields["nameIdentifier"] = forms.CharField(required=False, label=_("Name Identifier"))
    self.fields["nameIdentifier-nameIdentifierScheme"] = forms.CharField(required=False, label=_("Identifier Scheme"))
    self.fields["nameIdentifier-schemeURI"] = forms.CharField(required=False, label=_("Scheme URI"))
    self.fields["affiliation"] = forms.CharField(required=False, label=_("Affiliation"))
  def clean(self):
    cleaned_data = super(CreatorForm, self).clean()
    ni = cleaned_data.get("nameIdentifier")
    ni_s = cleaned_data.get("nameIdentifier-nameIdentifierScheme")
    ni_s_uri = cleaned_data.get("nameIdentifier-schemeURI")
    err = nameIdValidation(ni, ni_s, ni_s_uri)
    if err: raise ValidationError(err) 
    return cleaned_data

class TitleForm(forms.Form):
  """ Form object for Title Element in DataCite Advanced (XML) profile """
  def __init__(self, *args, **kwargs):
    super(TitleForm,self).__init__(*args,**kwargs)
    self.fields["title"] = forms.CharField(label=_("Title"),
      error_messages={'required': ERR_TITLE}) 
    TITLE_TYPES = (
      ("", _("Main title")),
      ("AlternativeTitle", _("Alternative title")),
      ("Subtitle", _("Subtitle")),
      ("TranslatedTitle", _("Translated title"))
    ) 
    self.fields["titleType"] = forms.ChoiceField(required=False, label = _("Type"),
      widget= forms.RadioSelect(), choices=TITLE_TYPES)
    self.fields["{http://www.w3.org/XML/1998/namespace}lang"] = forms.CharField(required=False,
      label="Language(Hidden)", widget= forms.HiddenInput())

class DescrForm(forms.Form):
  """ Form object for Description Element in DataCite Advanced (XML) profile """
  def __init__(self, *args, **kwargs):
    super(DescrForm,self).__init__(*args,**kwargs)
    self.fields["description"] = forms.CharField(required=False, label=_("Descriptive information"))
    DESCR_TYPES = (
      ("", _("Select a type of description")),
      ("Abstract", _("Abstract")),
      ("SeriesInformation", _("Series Information")),
      ("TableOfContents", _("Table of Contents")),
      ("Methods", _("Methods")),
      ("Other", _("Other")) 
    ) 
    self.fields["descriptionType"] = forms.ChoiceField(required=False, label = _("Type"),
      choices=DESCR_TYPES)
    self.fields["{http://www.w3.org/XML/1998/namespace}lang"] = forms.CharField(required=False,
      label="Language(Hidden)", widget= forms.HiddenInput())

class SubjectForm(forms.Form):
  """ Form object for Subject Element in DataCite Advanced (XML) profile """
  def __init__(self, *args, **kwargs):
    super(SubjectForm,self).__init__(*args,**kwargs)
    self.fields["subject"] = forms.CharField(required=False, label=_("Subject"))
    self.fields["subjectScheme"] = forms.CharField(required=False, label=_("Subject Scheme"))
    self.fields["schemeURI"] = forms.CharField(required=False, label=_("Scheme URI"))
    self.fields["{http://www.w3.org/XML/1998/namespace}lang"] = forms.CharField(required=False,
      label="Language(Hidden)", widget= forms.HiddenInput())

class ContributorForm(forms.Form):
  """ Form object for Contributor Element in DataCite Advanced (XML) profile """
  def __init__(self, *args, **kwargs):
    super(ContributorForm,self).__init__(*args,**kwargs)
    self.fields["contributorName"] = forms.CharField(required=False, label=_("Name"))
    self.fields["nameIdentifier"] = forms.CharField(required=False, label=_("Name Identifier"))
    self.fields["nameIdentifier-nameIdentifierScheme"] = forms.CharField(required=False, label=_("Identifier Scheme"))
    self.fields["nameIdentifier-schemeURI"] = forms.CharField(required=False, label=_("Scheme URI"))
    CONTRIB_TYPES = (
      ("", _("Select a type of contributor")),
      ("ContactPerson", _("Contact Person")),
      ("DataCollector", _("Data Collector")),
      ("DataCurator", _("Data Curator")),
      ("DataManager", _("Data Manager" )),
      ("Distributor", _("Distributor")),
      ("Editor", _("Editor")),
      ("Funder", _("Funder")),
      ("HostingInstitution", _("Hosting Institution")),
      ("Producer", _("Producer")),
      ("ProjectLeader", _("Project Leader")),
      ("ProjectManager", _("Project Manager")),
      ("ProjectMember", _("Project Member")),
      ("RegistrationAgency", _("Registration Agency")),
      ("RegistrationAuthority", _("Registration Authority")),
      ("RelatedPerson", _("Related Person")),
      ("Researcher", _("Researcher")),
      ("ResearchGroup", _("Research Group")),
      ("RightsHolder", _("Rights Holder")),
      ("Sponsor", _("Sponsor")),
      ("Supervisor", _("Supervisor")),
      ("WorkPackageLeader", _("Work Package Leader")),
      ("Other", _("Other"))
    ) 
    self.fields["contributorType"] = forms.ChoiceField(required=False, 
      label = _("Contributor Type"), choices=CONTRIB_TYPES)
    self.fields["affiliation"] = forms.CharField(required=False, label=_("Affiliation"))
  def clean(self):
    cleaned_data = super(ContributorForm, self).clean()
    import pdb; pdb.set_trace()
    err1 = {}
    cname = cleaned_data.get("contributorName")
    ctype = cleaned_data.get("contributorType")
    caff = cleaned_data.get("affiliation")
    ni = cleaned_data.get("nameIdentifier")
    ni_s = cleaned_data.get("nameIdentifier-nameIdentifierScheme")
    ni_s_uri = cleaned_data.get("nameIdentifier-schemeURI")
    """ Use of contributor element requires name and type be populated """
    if (cname or ctype or caff or ni or ni_s or ni_s_uri):
      if not cname:
        err1['contributorName'] = _("Contributor Name is required if you fill in contributor information.")
      if not ctype:
        err1['contributorType'] = _("Contributor Type is required if you fill in contributor information.")
    err2 = nameIdValidation(ni, ni_s, ni_s_uri)
    err = dict(err1.items() + err2.items())
    if err: raise ValidationError(err) 
    return cleaned_data

""" ToDo:
dates
altIds 
relIds
sizes
formats
rights
"""

class GeoLocForm(forms.Form):
  """ Form object for GeoLocation Element in DataCite Advanced (XML) profile """
  # Translators: A coordinate point  
  geoLocationPoint = forms.RegexField(required=False, label=_("Point"),
    regex='^(\-?\d+(\.\d+)?)\s+(\-?\d+(\.\d+)?)$',
    error_messages={'invalid': _("A Geolocation Point must be made up of two decimal numbers separated by a space.")})
  # Translators: A bounding box (with coordinates)
  geoLocationBox = forms.RegexField(required=False, label=_("Box"),
    regex='^(\-?\d+(\.\d+)?)\s+(\-?\d+(\.\d+)?)\s+(\-?\d+(\.\d+)?)\s+(\-?\d+(\.\d+)?)$',
    error_messages={'invalid': _("A Geolocation Box must be made up of four decimal numbers separated by a space.")})
  geoLocationPlace = forms.CharField(required=False, label=_("Place"))

def getIdForm_datacite_xml (form_coll=None, request=None):
  """ For Advanced Datacite elements 
      On GET, displays 'form_coll' (named tuple) data translated from XML doc
      On POST (when editing an ID or creating a new ID), uses request.POST

      Returns elements as dict of Django forms and formsets
      Fields in Django FormSets follow this naming convention:
         prefix-#-elementName      
      Thus the creatorName field in the third Creator fieldset would be named:
         creators-creator-2-creatorName                                     """
  # Initialize forms and FormSets
  remainder_form = nonrepeating_form = resourcetype_form = creator_set = \
    title_set = descr_set = subject_set = contributor_set = geoloc_set = None 
  CreatorSet = formset_factory(CreatorForm, formset=RequiredFormSet)
  TitleSet = formset_factory(TitleForm, formset=RequiredFormSet)
  DescrSet = formset_factory(DescrForm)
  SubjectSet = formset_factory(SubjectForm)
  ContributorSet = formset_factory(ContributorForm)
  GeoLocSet = formset_factory(GeoLocForm)
  if not form_coll: 
# On Create:GET
    if not request:  # Get an empty form
      P = shoulder = None 
# On Create:POST, Edit:POST
    elif request: 
      assert request.method == "POST"
      P = request.POST 
      shoulder = P['shoulder'] if 'shoulder' in P else None 
    remainder_form = RemainderForm(P, shoulder=shoulder, auto_id='%s')
    nonrepeating_form = NonRepeatingForm(P, auto_id='%s')
    resourcetype_form = ResourceTypeForm(P, auto_id='%s')
    creator_set = CreatorSet(P, prefix=PREFIX_CREATOR_SET, auto_id='%s')
    title_set = TitleSet(P, prefix=PREFIX_TITLE_SET, auto_id='%s')
    descr_set = DescrSet(P, prefix=PREFIX_DESCR_SET, auto_id='%s')
    subject_set = SubjectSet(P, prefix=PREFIX_SUBJECT_SET, auto_id='%s')
    contributor_set = ContributorSet(P, prefix=PREFIX_CONTRIBUTOR_SET, auto_id='%s')
    geoloc_set = GeoLocSet(P, prefix=PREFIX_GEOLOC_SET, auto_id='%s')
# On Edit:GET (Convert DataCite XML dict to form)
  else:
    # Note: Remainder form only needed upon ID creation
    nonrepeating_form = NonRepeatingForm(form_coll.nonRepeating, auto_id='%s')
    resourcetype_form = ResourceTypeForm(form_coll.resourceType, auto_id='%s')
    creator_set = CreatorSet(_inclMgmtData(form_coll.creators, PREFIX_CREATOR_SET),
      prefix=PREFIX_CREATOR_SET, auto_id='%s')
    title_set = TitleSet(_inclMgmtData(form_coll.titles, PREFIX_TITLE_SET),
      prefix=PREFIX_TITLE_SET, auto_id='%s')
    descr_set = DescrSet(_inclMgmtData(form_coll.descrs, PREFIX_DESCR_SET),
      prefix=PREFIX_DESCR_SET, auto_id='%s')
    subject_set = SubjectSet(_inclMgmtData(form_coll.subjects, PREFIX_SUBJECT_SET),
      prefix=PREFIX_SUBJECT_SET, auto_id='%s')
    contributor_set = ContributorSet(_inclMgmtData(form_coll.contributors, PREFIX_CONTRIBUTOR_SET),
      prefix=PREFIX_CONTRIBUTOR_SET, auto_id='%s')
    geoloc_set = GeoLocSet(_inclMgmtData(form_coll.geoLocations, PREFIX_GEOLOC_SET),
      prefix=PREFIX_GEOLOC_SET, auto_id='%s')
  return {'remainder_form': remainder_form, 'nonrepeating_form': nonrepeating_form,
    'resourcetype_form': resourcetype_form, 'creator_set': creator_set, 
    'title_set': title_set, 'descr_set':descr_set, 'subject_set':subject_set, 
    'contributor_set':contributor_set, 'geoloc_set': geoloc_set}

def _inclMgmtData(fields, prefix):
  """ Only to be used for formsets with syntax <prefix>-#-<field>
      Build Req'd Management Form fields (basically counting # of forms in set) 
      based on Formset specs. Consult Django documentation titled: 'Understanding the ManagementForm' 
  """
  i_total = 0 
  if fields and prefix in list(fields)[0]:
    for f in fields:
      m = re.match("^.*-(\d+)-", f)
      s = m.group(1) 
      i = int(s) + 1   # First form is numbered '0', so add 1 for actual count 
      if i > i_total: i_total = i
  else:
    fields = {}
    i_total = 1   # Assume a form needs to be produced even if no data is being passed in
  fields[prefix + "-TOTAL_FORMS"] = str(i_total)
  fields[prefix + "-INITIAL_FORMS"] = '0'
  fields[prefix + "-MAX_NUM_FORMS"] = '1000'
  fields[prefix + "-MIN_NUM_FORMS"] = '0'
  return fields

def isValidDataciteXmlForm(form):
  """ Validate all forms and formsets included. Just pass empty or unbound form objects. 
      Returns false if one or more items don't validate
  """
  numFailed = 0 
  for f,v in form.iteritems(): 
    if v is None:
      r = True
    else: 
      r = True if not v.is_bound else v.is_valid()
    if not r: numFailed += 1 
  return (numFailed == 0)
  
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
############## Remaining Forms (not related to ID creation/editing) #########

################# User Form Validation functions  #################

def _validate_proxies(proxies):
  p_list = [p.strip() for p in proxies.split(',')]
  for proxy in p_list:
    try:
      # ToDo: Make sure this validates a proxy user and not a coowner like it's doing now.
      idmap.getUserId(proxy)
    except AssertionError:
      raise ValidationError(proxy + " " + \
        _("is not a correct username for a co-owner."))

def _validate_current_pw(username):
  def innerfn(pwcurrent):
    auth = userauth.authenticate(username, request.POST["pwcurrent"])
    if type(auth) is str or not auth:
      raise ValidationError(_("Your current password is incorrect."))
  return innerfn

################# User (My Account) Form  #################

class UserForm(forms.Form):
  """ Form object for My Account Page (User editing) """
  username = '' 
  def __init__(self, *args, **kwargs):
    username = kwargs.pop('username',None)
    super(UserForm,self).__init__(*args,**kwargs)
  givenName = forms.CharField(required=False, label=_("First Name"))
  sn = forms.CharField(label=_("Last Name"),
    error_messages={'required': _("Please fill in your last name")})
  telephoneNumber = forms.CharField(required=False, label=_("Phone"))
  mail = forms.EmailField(label=_("Email Address"),
    error_messages={'required': _("Please fill in your email."),
                    'invalid': _("Please fill in a valid email address.")})
  ezidCoOwners = forms.CharField(required=False, label=_("Proxy User(s)"),
    validators=[_validate_proxies])
  pwcurrent = forms.CharField(required=False, label=_("Current Password"),
    widget=forms.PasswordInput(), validators=[_validate_current_pw(username)])
  pwnew = forms.CharField(required=False, label=_("New Password"),
    widget=forms.PasswordInput())
  pwconfirm = forms.CharField(required=False, label=_("Confirm New Password"),
    widget=forms.PasswordInput())
  def clean(self):
    cleaned_data = super(UserForm, self).clean()
    pwnew_c = cleaned_data.get("pwnew")
    pwconfirm_c = cleaned_data.get("pwconfirm")
    if pwnew_c and pwnew_c != pwconfirm_c:
      raise ValidationError("Passwords don't match")
    return cleaned_data

################# Search ID Form  #################

class BaseSearchIdForm(forms.Form):
  """ Base form object used for public Search ID page, 
      and extended for use with Manage ID page        """
  keywords = forms.CharField(required=False, label=_("Search Terms"),
    widget=forms.TextInput(attrs={'placeholder': _("Full text search using words about or describing the identifier.")}))
  # ToDo: Determine proper regex for identifier for validation purposes
  identifier = forms.CharField(required=False, 
    label=_("Identifier/Identifier Prefix"), widget=forms.TextInput(
      attrs={'placeholder': "doi:10.17614/Q44F1NB79"}))
  # Translators: "Ex." is abbreviation for "example"
  title = forms.CharField(required=False, label=_("Object Title (What)"),
    widget=forms.TextInput(attrs={'placeholder': _("Ex.") + \
      "2,2,2-trichloro-1-[(4R)-3,3,4-trimethyl-1,1-dioxo-thiazetidin-2-yl]ethanone"}))
  creator = forms.CharField(required=False, label=_("Object Creator (Who)"),
    widget=forms.TextInput(attrs={'placeholder': 
      _("Ex. Pitt Quantum Repository")}))
  publisher = forms.CharField(required=False, label=_("Object Publisher"),
    widget=forms.TextInput(attrs={'placeholder': 
      _("Ex. University of Pittsburgh")}))
  pubyear_from = forms.RegexField(required=False, label=_("From"),
    regex='^\d{4}$',
    error_messages={'invalid': ERR_4DIGITYEAR },
    widget=forms.TextInput(attrs={'placeholder': _("Ex. 2015")}))
  pubyear_to = forms.RegexField(required=False, label=_("To"),
    regex='^\d{4}$', 
    error_messages={'invalid': ERR_4DIGITYEAR },
    widget=forms.TextInput(attrs={'placeholder': _("Ex. 2016")}))
  object_type = forms.ChoiceField(required=False, choices=RESOURCE_TYPES, 
    label = _("Object Type"))
  ID_TYPES = (
    ('', _("Select a type of identifier (ARK or DOI)")),
    ('ark', "ARK"),
    ('doi', "DOI"),
  )
  id_type = forms.ChoiceField(required=False, choices=ID_TYPES, 
    label = _("Identifier Type"))
  def clean(self):
    """ Invalid if all fields are empty """
    field_count = len(self.fields)
    cleaned_data = super(BaseSearchIdForm, self).clean()
    """ cleaned_data contains all valid fields. So if one or more fields
        are invalid, we need to simply bypass this check for non-empty fields"""
    if len(cleaned_data) < field_count:
      return cleaned_data
    form_empty = True
    for field_value in cleaned_data.itervalues():
      # Check for None or '', so IntegerFields with 0 or similar things don't seem empty.
      if field_value is not None and field_value != '' and not field_value.isspace():
        form_empty = False
        break
    if form_empty:
      raise forms.ValidationError(_("Please enter information in at least one field."))
    return cleaned_data

class ManageSearchIdForm(BaseSearchIdForm):
  """ Used for Searching on Manage ID page. Inherits from BaseSearchIdForm """ 
  target = forms.CharField(required=False, label=_("Target URL"),
    widget=forms.TextInput(attrs={'placeholder': _("Ex. http://pqr.pitt.edu/mol/KQSWENSZQKJHSQ-SCSAIBSYSA-N")}))
  create_time_from = forms.RegexField(required=False, label=_("From"),
    regex='^\d{4}-\d{2}-\d{2}$',
    error_messages={'invalid': _("Please fill in a date using format YYYY-MM-DD.")},
    widget=forms.TextInput(attrs={'placeholder': _("Ex. 2015-08-13")}))
  create_time_to = forms.RegexField(required=False, label=_("To"),
    regex='^\d{4}-\d{2}-\d{2}$',
    error_messages={'invalid': _("Please fill in a date using format YYYY-MM-DD.")},
    widget=forms.TextInput(attrs={'placeholder': _("Ex. 2015-08-13")}))
  update_time_from = forms.RegexField(required=False, label=_("From"),
    regex='^\d{4}-\d{2}-\d{2}$',
    error_messages={'invalid': _("Please fill in a date using format YYYY-MM-DD.")},
    widget=forms.TextInput(attrs={'placeholder': _("Ex. 2015-08-13")}))
  update_time_to = forms.RegexField(required=False, label=_("To"),
    regex='^\d{4}-\d{2}-\d{2}$',
    error_messages={'invalid': _("Please fill in a date using format YYYY-MM-DD.")},
    widget=forms.TextInput(attrs={'placeholder': _("Ex. 2015-08-13")}))
  ID_STATUS = (
    ('', _("Select a status")),
    ('public', "Public"),
    ('reserved', "Reserved"),
    ('unavailable', "Unavailable"),
  )
  id_status = forms.ChoiceField(required=False, choices=ID_STATUS, 
    label = _("Identifier Status"))
  harvesting = forms.BooleanField(label=_("Allows Harvesting/Indexing?"),
    widget=forms.RadioSelect(choices=((True, 'Yes'), (False, 'No'))))
  hasMetadata = forms.BooleanField(label=_("Has Metadata?"),
    widget=forms.RadioSelect(choices=((True, 'Yes'), (False, 'No'))))

################# Contact Us Form  #################

class ContactForm(forms.Form):
  """ Form object for Contact Us form """
  # Translators: These options will appear in drop-down on contact page
  CONTACT_REASONS = (
    ("", _("Choose One")),
    ("account_new", _("I would like to inquire about getting a new account")),
    ("account_existing", _("I have a problem or question about existing account")),
    ("newsletter", _("I'd like to sign up for the EZID email newsletter")),
    ("other", _("Other")),
  )
  contact_reason = forms.ChoiceField(required=False, choices=CONTACT_REASONS, 
    label = _("Reason for contacting EZID"))
  your_name = forms.CharField(max_length=200, label=_("Your Name"),
    error_messages={'required': _("Please fill in your name")})
  email = forms.EmailField(max_length=200, label=_("Your Email"),
    error_messages={'required': _("Please fill in your email."),
                    'invalid': _("Please fill in a valid email address.")})
  affiliation = forms.CharField(required=False, label=_("Your Institution"), 
    max_length=200)
  comment = forms.CharField(label=_("Please indicate any question or comment you may have"), 
    widget=forms.Textarea(attrs={'rows': '4'}),
    error_messages={'required': _("Please fill in a question or comment.")})

  # Translators: These options appear in drop-down on contact page
  REFERRAL_SOURCES = (
    ("", _("Choose One")),
    ("website", _("Website")),
    ("conference", _("Conference")),
    ("colleagues", _("Colleagues")),
    ("webinar", _("Webinar")),
    ("other", _("Other")),
  )
  hear_about = forms.ChoiceField(required=False, choices=REFERRAL_SOURCES,
    label=_("How did you hear about us?"))
  test = forms.CharField(label="Hidden",required=False, widget=forms.HiddenInput())

################  Password Reset Landing Page ##########

class PwResetLandingForm(forms.Form):
  username=forms.CharField(label=_("Username"),
    error_messages={'required': _("Please fill in your username.")})
  email=forms.EmailField(label=_("Email address"),
    error_messages={'required': _("Please fill in your email address."),
                    'invalid': _("Please fill in a valid email address.")})
  """ Strip any surrounding whitespace """
  # ToDo: This doesn't seem to work. It also need to be done for email.
  def clean_username(self):
    username = self.cleaned_data["username"].strip()
    return username
