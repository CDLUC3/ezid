from django import forms
import ui_common as uic
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

def _validate_url(url):
  if not uic.url_is_valid(url):
    raise ValidationError(_("Please enter a a valid location (URL)"))

class ErcForm(forms.Form):
  """ Form object for ID with ERC profile """
  _target = forms.CharField(required=False, label=_("Location (URL)"),
    validators=[_validate_url])
  def __init__(self, *args, **kwargs):
    super(forms.Form,self).__init__(*args,**kwargs)
    self.fields["erc.who"]=forms.CharField(required=False, label=_("Who"))
    self.fields["erc.what"]=forms.CharField(required=False, label=_("What"))
    self.fields["erc.when"]=forms.CharField(required=False, label=_("When"))

class DcForm(forms.Form):
  """ Form object for ID with Dublin Core profile """
  _target = forms.CharField(required=False, label=_("Location (URL)"),
    validators=[_validate_url])
  def __init__(self, *args, **kwargs):
    super(forms.Form,self).__init__(*args,**kwargs)
    self.fields["dc.creator"] = forms.CharField(required=False, label=_("Creator"))
    self.fields["dc.title"] = forms.CharField(required=False, label=_("Title"))
    self.fields["dc.publisher"] = forms.CharField(required=False, label=_("Publisher"))
    self.fields["dc.date"] = forms.CharField(required=False, label=_("Date"))
    self.fields["dc.type"] = forms.CharField(required=False, label=_("Type"))

class DataciteForm(forms.Form):
  """ Form object for ID with DataCite profile """
  _target = forms.CharField(required=False, label=_("Location (URL)"),
    validators=[_validate_url])
  def __init__(self, *args, **kwargs):
    super(forms.Form,self).__init__(*args,**kwargs)
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

def getIdForm (profile, request=None):
  if request: assert request.method == 'POST'
  r = request.POST if request else None
  if profile.name == 'erc': return ErcForm(r)
  elif profile.name == 'datacite': return DataciteForm(r)
  elif profile.name == 'dc': return DcForm(r)
    
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
