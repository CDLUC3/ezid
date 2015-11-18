from django import forms
from django.forms import formset_factory
import ui_common as uic
import util
import idmap
import userauth 
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

remainder_box_default = _("Recommended: Leave blank")

################# Basic ID Forms ####################

class BaseForm(forms.Form):
  """ Base Form object: all forms have a _target field  """
  def __init__(self, *args, **kwargs):
    super(BaseForm,self).__init__(*args,**kwargs)
    self.fields["_target"]=forms.CharField(required=False, label=_("Location (URL)"),
      validators=[_validate_url])

class ErcForm(BaseForm):
  """ Form object for ID with ERC profile. BaseForm parent brings in _target field """
  def __init__(self, *args, **kwargs):
    super(ErcForm,self).__init__(*args,**kwargs)
    self.fields["erc.who"]=forms.CharField(required=False, label=_("Who"))
    self.fields["erc.what"]=forms.CharField(required=False, label=_("What"))
    self.fields["erc.when"]=forms.CharField(required=False, label=_("When"))

class DcForm(BaseForm):
  """ Form object for ID with Dublin Core profile. BaseForm parent brings in 
      _target field """
  def __init__(self, *args, **kwargs):
    super(DcForm,self).__init__(*args,**kwargs)
    self.fields["dc.creator"] = forms.CharField(required=False, label=_("Creator"))
    self.fields["dc.title"] = forms.CharField(required=False, label=_("Title"))
    self.fields["dc.publisher"] = forms.CharField(required=False, label=_("Publisher"))
    self.fields["dc.date"] = forms.CharField(required=False, label=_("Date"))
    self.fields["dc.type"] = forms.CharField(required=False, label=_("Type"))

class DataciteForm(BaseForm):
  """ Form object for ID with DataCite profile. BaseForm parent brings in 
      _target field """
  def __init__(self, *args, **kwargs):
    super(DataciteForm,self).__init__(*args,**kwargs)
    self.fields["datacite.creator"] = forms.CharField(label=_("Creator"),
      error_messages={'required': _("Please fill in a value for creator.")})
    self.fields["datacite.title"] = forms.CharField(label=_("Title"),
      error_messages={'required': _("Please fill in a value for title.")})
    self.fields["datacite.publisher"] = forms.CharField(label=_("Publisher"),
      error_messages={'required': _("Please fill in a value for publisher.")})
    self.fields["datacite.publicationyear"] = forms.RegexField(label=_("Publication year"),
      regex='^\d{4}|\(:unac\)|\(:unal\)|\(:unap\)|\(:unas\)|\(:unav\)|\(:unkn\)| \
        \(:none\)|\(:null\)|\(:tba\)|\(:etal\)|\(:at\)$',
      error_messages={'required': _("Please fill in a value for publication year."),
                    'invalid': _("Please fill in a  4-digit publication year.")})
    # Translators: These options appear in drop-down on ID Creation page (DOIs)
    RESOURCE_TYPES = (
      ('', _('[Select a type of resource]')), ('Audiovisual', _('Audiovisual')), 
      ('Collection', _('Collection')), ('Dataset', _('Dataset')), 
      ('Event', _('Event')), ('Image', _('Image')), 
      ('InteractiveResource', _('InteractiveResource')), ('Model', _('Model')), 
      ('PhysicalObject', _('PhysicalObject')), ('Service', _('Service')), 
      ('Software', _('Software')), ('Sound', _('Sound')), ('Text', _('Text')), 
      ('Workflow', _('Workflow')), ('Other', _('Other'))
    )
    self.fields["datacite.resourcetype"] = forms.ChoiceField(required=False, 
      choices=RESOURCE_TYPES, label=_("Resource type"))

# Returns a simple ID Django form
def getIdForm (profile, request=None):
  P = None
  if request:
    assert request.method == 'POST'
    P = request.POST
  if profile.name == 'erc': return ErcForm(P)
  elif profile.name == 'datacite': return DataciteForm(P)
  elif profile.name == 'dc': return DcForm(P)

################# Advanced ID Form Retrieval - (two forms technically) #######

class RemainderForm(forms.Form):
  """ Remainder Form object: all advanced forms have a remainder field,
      validation of which requires passing in the shoulder """
  def __init__(self, *args, **kwargs):
    self.shoulder = kwargs.pop('shoulder',None)
    super(RemainderForm,self).__init__(*args,**kwargs)
    self.fields["remainder"]=forms.CharField(required=False, 
      label=_("Custom Remainder"), initial=remainder_box_default, 
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
    test = "" if remainder_to_test == remainder_box_default \
      else remainder_to_test
    # ToDo: change this to util.validateIdentifier when this code is brought in
    if not (util.validateArk(shoulder[5:] + test)):
      raise ValidationError(
        _("This combination of characters cannot be used as a remainder."))
  return innerfn

################# Advanced Datacite ID Form/Elements #################

class CreatorForm(forms.Form):
  """ Form object for Creator Element in DataCite Advanced (XML) profile """
  def __init__(self, *args, **kwargs):
    super(forms.Form,self).__init__(*args,**kwargs)
    self.fields["/resource/creators/creator[1]/creatorName"] =  \
      forms.CharField(label=_("Name"))
    self.fields["/resource/creators/creator[1]/nameIdentifier"] = \
      forms.CharField(label=_("Name Identifier"))

class TitleForm(forms.Form):
  """ Form object for Title Element in DataCite Advanced (XML) profile """
  def __init__(self, *args, **kwargs):
    super(forms.Form,self).__init__(*args,**kwargs)
    self.fields["/resource/titles/title[1]"] = \
      forms.CharField(label=_("Title"))

# Returns *Advanced* Datacite elements in the form of Django formsets
def getIdForm_datacite_xml (request=None):
  if request: assert request.method == 'POST'
  P = request.POST if request else None
  CreatorSet = formset_factory(CreatorForm)
  TitleSet = formset_factory(TitleForm)
  if not P:    # GET
    remainder_form = RemainderForm(P, shoulder=None, auto_id='%s')
    creator_set = CreatorSet(prefix='creators')
    title_set = TitleSet(prefix='titles')
  else:
    remainder_form = RemainderForm(P, shoulder=P['shoulder'], auto_id='%s')
    creator_set = CreatorSet(P, prefix='creators')
    title_set = TitleSet(P, prefix='titles')
  return {'remainder_form': remainder_form, 'creator_set': creator_set, 
    'title_set': title_set}

#############################################################################
############## Remaining Forms (not related to ID creation/editing) #########
#############################################################################

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
  ezidCoOwners = forms.CharField(required=False, label=_("Assigned Proxy Users"),
    validators=[_validate_proxies])
  pwcurrent = forms.CharField(required=False, label=_("Current Password"),
    validators=[_validate_current_pw(username)])
  pwnew = forms.CharField(required=False, label=_("New Password"))
  pwconfirm = forms.CharField(required=False, label=_("Confirm New Password"))
  def clean(self):
    cleaned_data = super(UserForm, self).clean()
    pwnew_c = cleaned_data.get("pwnew")
    pwconfirm_c = cleaned_data.get("pwconfirm")
    if pwnew_c and pwnew_c != pwconfirm_c:
      raise ValidationError("Passwords don't match")
    return cleaned_data

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
  def clean_username(self):
    username = self.cleaned_data["username"].strip()
    return username
