from django import forms
from django.forms import BaseFormSet, formset_factory
import ui_common as uic
import util
import idmap
import userauth 
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

################# Constants ####################

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
REGEX_4DIGITYEAR='^\d{4}|\(:unac\)|\(:unal\)|\(:unap\)|\(:unas\)|\(:unav\)|\
  \(:unkn\)|\(:none\)|\(:null\)|\(:tba\)|\(:etal\)|\(:at\)$'

################# Basic ID Forms ####################

class BaseForm(forms.Form):
  """ Base Form object: all forms have a _target field. If 'placeholder' is True
      set attribute to include specified placeholder text in text fields """
  def __init__(self, *args, **kwargs):
    self.placeholder = kwargs.pop('placeholder',None)
    super(BaseForm,self).__init__(*args,**kwargs)
    self.fields["_target"]=forms.CharField(required=False, label=_("Location (URL)"),
      validators=[_validate_url])
    if self.placeholder is not None and self.placeholder == True:
      self.fields['_target'].widget.attrs['placeholder'] = _("Location (URL)")

class ErcForm(BaseForm):
  """ Form object for ID with ERC profile (Used for simple or advanced ARK).
      BaseForm parent brings in _target field. If 'placeholder' is True 
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
    super(DcForm,self).__init__(*args,**kwargs)
    self.fields["dc.creator"] = forms.CharField(required=False, label=_("Creator"))
    self.fields["dc.title"] = forms.CharField(required=False, label=_("Title"))
    self.fields["dc.publisher"] = forms.CharField(required=False, label=_("Publisher"))
    self.fields["dc.date"] = forms.CharField(required=False, label=_("Date"))
    self.fields["dc.type"] = forms.CharField(required=False, label=_("Type"))

class DataciteForm(BaseForm):
  """ Form object for ID with (simple DOI) DataCite profile. BaseForm parent brings in 
      _target field. If 'placeholder' is True set attribute to include specified
      placeholder text in text fields """
  def __init__(self, *args, **kwargs):
    super(DataciteForm,self).__init__(*args,**kwargs)
    self.fields["datacite.creator"] = forms.CharField(label=_("Creator"),
      error_messages={'required': _("Please fill in a value for creator.")})
    self.fields["datacite.title"] = forms.CharField(label=_("Title"),
      error_messages={'required': _("Please fill in a value for title.")})
    self.fields["datacite.publisher"] = forms.CharField(label=_("Publisher"),
      error_messages={'required': _("Please fill in a value for publisher.")})
    self.fields["datacite.publicationyear"] = forms.RegexField(label=_("Publication year"),
      regex=REGEX_4DIGITYEAR,
      error_messages={'required': _("Please fill in a value for publication year."),
                    'invalid': _("Please fill in a 4-digit publication year.")})
    # Translators: These options appear in drop-down on ID Creation page (DOIs)
    self.fields["datacite.resourcetype"] = \
      forms.ChoiceField(required=False, choices=RESOURCE_TYPES, label=_("Resource type"))
    if self.placeholder is not None and self.placeholder == True:
      self.fields['datacite.creator'].widget.attrs['placeholder'] = _("Creator")
      self.fields['datacite.title'].widget.attrs['placeholder'] = _("Title")
      self.fields['datacite.publisher'].widget.attrs['placeholder'] = _("Publisher")
      self.fields['datacite.publicationyear'].widget.attrs['placeholder'] = _("Publication year")

def getIdForm (profile, placeholder, request=None):
  """ Returns a simple ID Django form. If 'placeholder' is True
      set attribute to include specified placeholder text in text fields """
  P = None
  if request:
    assert request.method == 'POST'
    P = request.POST
  if profile.name == 'erc': 
    form = ErcForm(P, placeholder=placeholder)
  elif profile.name == 'datacite': 
    form = DataciteForm(P, placeholder=placeholder)
  elif profile.name == 'dc': 
    form = DcForm(P, placeholder=placeholder)
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
  P = None
  shoulder = None
  if request: 
    assert request.method == 'POST'
    P = request.POST
    shoulder=P['shoulder']
  remainder_form = RemainderForm(P, shoulder=shoulder, auto_id='%s')
  if profile.name == 'erc': form = ErcForm(P, auto_id='%s')
  elif profile.name == 'datacite': form = DataciteForm(P, auto_id='%s')
  elif profile.name == 'dc': form = DcForm(P, auto_id='%s')
  return {'remainder_form': remainder_form, 'form': form}

################# ID Form Validation functions  #################

def _validate_url(url):
  if not uic.url_is_valid(url):
    raise ValidationError(_("Please enter a valid location (URL)"))

def _validate_custom_remainder(shoulder):
  def innerfn(remainder_to_test):
    test = "" if remainder_to_test == REMAINDER_BOX_DEFAULT \
      else remainder_to_test
    if not (util.validateIdentifier(shoulder + test)):
      raise ValidationError(
        _("This combination of characters cannot be used as a remainder."))
  return innerfn

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
################# Advanced Datacite ID Form/Elements #################

class NonRepeatingForm(forms.Form):
  """ Form object for single field elements in DataCite Advanced (XML) profile """
  target=forms.CharField(required=False, label=_("Location (URL)"),
    validators=[_validate_url])
  publisher = forms.CharField(label=_("Publisher"))
  publicationYear = forms.RegexField(label=_("Publication Year"),
    regex=REGEX_4DIGITYEAR,
    error_messages={'required': _("Please fill in a value for publication year."),
                    'invalid': _("Please fill in a 4-digit publication year.")})
  language = forms.CharField(required=False, label=_("Language"))
  version = forms.CharField(required=False, label=_("Version"))

class ResourceTypeForm(forms.Form):
  """ This is also composed of single field elements like NonRepeatingForm,
      but I wasn't sure how to display fields with hyphens directly in the template.
      By embedding them in a form object, this bypasses that problem. """
  def __init__(self, *args, **kwargs):
    super(ResourceTypeForm,self).__init__(*args,**kwargs)
    self.fields['resourceType-ResourceTypeGeneral'] = forms.ChoiceField(choices=RESOURCE_TYPES, label = _("Resource Type General"))
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
    self.fields["creatorName"] = forms.CharField(label=_("Name"))
    self.fields["nameIdentifier"] = forms.CharField(required=False, label=_("Name Identifier"))
    self.fields["nameIdentifier-nameIdentifierScheme"] = forms.CharField(required=False, label=_("Identifier Scheme"))
    self.fields["nameIdentifier-schemeURI"] = forms.CharField(required=False, label=_("Scheme URI"))
    self.fields["affiliation"] = forms.CharField(required=False, label=_("Affiliation"))

class TitleForm(forms.Form):
  """ Form object for Title Element in DataCite Advanced (XML) profile """
  def __init__(self, *args, **kwargs):
    super(TitleForm,self).__init__(*args,**kwargs)
    self.fields["title"] = forms.CharField(label=_("Title"))
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

class GeoLocForm(forms.Form):
  """ Form object for GeoLocation Element in DataCite Advanced (XML) profile """
  # Translators: A coordinate point  
  geoLocationPoint = forms.RegexField(required=False, label=_("Point"),
    regex='^(\-?\d+(\.\d+)?)\s+(\-?\d+(\.\d+)?)$',
    error_messages={'invalid': _("A Geolocation Point must be made up of two \
      decimal numbers separated by a space.")})
  # Translators: A bounding box (with coordinates)
  geoLocationBox = forms.RegexField(required=False, label=_("Box"),
    regex='^(\-?\d+(\.\d+)?)\s+(\-?\d+(\.\d+)?)\s+(\-?\d+(\.\d+)?)\s+(\-?\d+(\.\d+)?)$',
    error_messages={'invalid': _("A Geolocation Box must be made up of four \
      decimal numbers separated by a space.")})
  geoLocationPlace = forms.CharField(required=False, label=_("Place"))

def getIdForm_datacite_xml (d=None, request=None):
  """ Accepts request.POST for base level variables (and when creating a new ID),
      When displaying an already created ID, accepts a dictionary of datacite_xml
      specific data.
      Returns Advanced Datacite elements as dict of Django forms and formsets
      Fields in Django FormSets follow this naming convention:
         prefix-#-elementName      
      Thus the creatorName field in the third Creator fieldset would be named:
         creators-creator-1-creatorName                                     """
  # Initialize forms and FormSets
  remainder_form = nonrepeating_form = resourcetype_form = creator_set = \
    title_set = geoloc_set = None 
  CreatorSet = formset_factory(CreatorForm, formset=RequiredFormSet)
  TitleSet = formset_factory(TitleForm, formset=RequiredFormSet)
  GeoLocSet = formset_factory(GeoLocForm)
  # On Create:GET
  if not request and not d:  # Get an empty form
    remainder_form = RemainderForm(None, shoulder=None, auto_id='%s')
    nonrepeating_form = NonRepeatingForm(None, auto_id='%s')
    resourcetype_form = ResourceTypeForm(None, auto_id='%s')
    creator_set = CreatorSet(prefix='creators-creator')
    title_set = TitleSet(prefix='titles-title')
    geoloc_set = GeoLocSet(prefix='geoLocations-geoLocation')
  # On Edit:GET (Convert DataCite XML dict to form)
  elif request and request.method == "GET":
    assert d is not None
    # Remainder form only needed upon ID creation
    nonrepeating_form = NonRepeatingForm(d['dx_dict']['nonRepeating'], auto_id='%s')
    resourcetype_form = ResourceTypeForm(d['dx_dict']['resourceType'], auto_id='%s')
    creator_set = CreatorSet(d['dx_dict']['creators'], prefix='creators-creator', auto_id='%s')
    title_set = TitleSet(d['dx_dict']['titles'], prefix='titles-title', auto_id='%s')
    geoloc_set = GeoLocSet(d['dx_dict']['geoLocations'], prefix='geoLocations-geoLocation', auto_id='%s')
  # On Create:POST, Edit:POST
  elif request and request.method == "POST": 
    P = request.POST 
    shoulder = P['shoulder'] 
    remainder_form = RemainderForm(P, shoulder=shoulder, auto_id='%s')
    nonrepeating_form = NonRepeatingForm(P, auto_id='%s')
    resourcetype_form = ResourceTypeForm(P, auto_id='%s')
    creator_set = CreatorSet(P, prefix='creators-creator', auto_id='%s')
    title_set = TitleSet(P, prefix='titles-title', auto_id='%s')
    geoloc_set = GeoLocSet(P, prefix='geoLocations-geoLocation', auto_id='%s')
  return {'remainder_form': remainder_form, 'nonrepeating_form': nonrepeating_form,
    'resourcetype_form': resourcetype_form, 'creator_set': creator_set, 
    'title_set': title_set, 'geoloc_set' : geoloc_set}

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
    widget=forms.TextInput(attrs={'placeholder': _("Ex. 2,2,2-trichloro-1-[(4R)-3,3,4-trimethyl-1,1-dioxo-thiazetidin-2-yl]ethanone")}))
  creator = forms.CharField(required=False, label=_("Object Creator (Who)"),
    widget=forms.TextInput(attrs={'placeholder': 
      _("Ex. Pitt Quantum Repository")}))
  publisher = forms.CharField(required=False, label=_("Object Publisher"),
    widget=forms.TextInput(attrs={'placeholder': 
      _("Ex. University of Pittsburgh")}))
  pubyear_from = forms.RegexField(required=False, label=_("From"),
    regex='^\d{1,4}$',
    error_messages={'invalid': _("Please fill in a 4-digit publication year.")},
    widget=forms.TextInput(attrs={'placeholder': _("Ex. 2015")}))
  pubyear_to = forms.RegexField(required=False, label=_("To"),
    regex='^\d{1,4}$', 
    error_messages={'invalid': _("Please fill in a 4-digit publication year.")},
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
    ("account_existing", _("I have a problem or question about existing \
      account")),
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
  comment = forms.CharField(label=_("Please indicate any question or comment \
    you may have"), widget=forms.Textarea(attrs={'rows': '4'}),
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
