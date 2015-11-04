from django import forms
from django.utils.translation import ugettext as _

class ContactForm(forms.Form):
  """
  Form object for Contact Us form 
  'attrs' parameter passes in arguments for proper display in UI
  (eg. class="form-control" is specific to Bootstrap UI framework)
  """
  # Translators: These options will appear in drop-down on contact page
  CONTACT_REASONS = (
    ("", _("Choose One")),
    ("account_new", _("I would like to inquire about getting a new account")),
    ("account_existing", _("I have a problem or question about existing \
      account")),
    ("newsletter", _("I'd like to sign up for the EZID email newsletter")),
    ("other", _("Other")),
  )
  contact_reason = forms.ChoiceField(choices=CONTACT_REASONS, 
    label = _("Reason for contacting EZID"))
  your_name = forms.CharField(max_length=200, label=_("Your Name"))
  email = forms.EmailField(max_length=200, label=_("Your Email"))
  affiliation = forms.CharField(required=False, label=_("Your Institution"), 
    max_length=200)
  comment = forms.CharField(label=_("Please indicate any question or comment \
    you may have"), widget=forms.Textarea(attrs={'rows': '4'}))

  # Translators: These options appear in drop-down on contact page
  REFERRAL_SOURCES = (
    ("", _("Choose One")),
    ("website", _("Website")),
    ("conference", _("Conference")),
    ("colleagues", _("Colleagues")),
    ("webinar", _("Webinar")),
    ("other", _("Other")),
  )
  hear_about = forms.ChoiceField(choices=REFERRAL_SOURCES,
    label=_("How did you hear about us?"))
