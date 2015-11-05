from django import forms
from django.utils.translation import ugettext as _

class ProfileErcForm(forms.Form):
  """
  Form object for ID with ERC profile 
  """
  erc_who = forms.CharField(required=False, label=_("Who"))
  erc_what = forms.CharField(required=False, label=_("What"))
  erc_when = forms.CharField(required=False, label=_("When"))

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
    error_messages={'required': _('Please fill in your name')})
  email = forms.EmailField(max_length=200, label=_("Your Email"),
    error_messages={'required': _('Please fill in your email.'),
                    'invalid': _('Please fill in a valid email address.')})
  affiliation = forms.CharField(required=False, label=_("Your Institution"), 
    max_length=200)
  comment = forms.CharField(label=_("Please indicate any question or comment \
    you may have"), widget=forms.Textarea(attrs={'rows': '4'}),
    error_messages={'required': _('Please fill in a question or comment.')})

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
