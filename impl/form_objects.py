import re

import django.core.validators
from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseFormSet, formset_factory
from django.utils.translation import ugettext as _

import ezidapp.models
import geometry_util
import ui_common as uic
import userauth
import util

""" Django form framework added in 2016 release of EZID UI.
    Bulk of form validation occurs here. Avoiding JavaScript form validation
    in most cases in the UI.

    Fields with hyphens, periods or leading underscores cause issues in python and in these cases
    are defined using the fields dictionary of the Form class
    i.e. self.fields["erc.who"] = ...

    Designating a field as required involves:
      * remove required=false from field definition
      * (optional) include custom error text in the field's error_messages['required'] variable
      * properly label the field within the template by including reqd="true"
        i.e. Including a required select field for an advanced datacite ID:
        {% include "create/_datacite_inlineselect.html" with field=rt_field reqd="true" %}
        It's done in template "includes/_inline.....html" for all other form types

    CSS styling (using "class=") is done using the add_attributes template tag
      in ui_tags/templatetags/layout_extras.py
    But for radio buttons this doesn't work for some reason, and so is being initialized here
    i.e. forms.RadioSelect(attrs={'class': 'fcontrol__radio-button-stacked'})
"""

#### Constants ####

REMAINDER_BOX_DEFAULT = _("Recommended: Leave blank")
RESOURCE_TYPES = (
    ('', _("Select a type of object")),
    ('Audiovisual', _('Audiovisual')),
    ('Collection', _('Collection')),
    ('Dataset', _('Dataset')),
    ('Event', _('Event')),
    ('Image', _('Image')),
    ('InteractiveResource', _('Interactive Resource')),
    ('Model', _('Model')),
    ('PhysicalObject', _('Physical Object')),
    ('Service', _('Service')),
    ('Software', _('Software')),
    ('Sound', _('Sound')),
    ('Text', _('Text')),
    ('Workflow', _('Workflow')),
    ('Other', _('Other')),
)
REGEX_4DIGITYEAR = '^(\d{4}|\(:unac\)|\(:unal\)|\(:unap\)|\(:unas\)|\(:unav\)|\
   \(:unkn\)|\(:none\)|\(:null\)|\(:tba\)|\(:etal\)|\(:at\))$'
REGEX_GEOPOINT = '-?(\d+(\.\d*)?|\.\d+)$'
# http://stackoverflow.com/questions/3962543/how-can-i-validate-a-culture-code-with-a-regular-expression
REGEX_LANGUAGE = '^[a-z]{2,3}(?:-[A-Z]{2,3}(?:-[a-zA-Z]{4})?)?$'
ERR_4DIGITYEAR = _("Four digits required")
ERR_DATE = _("Please use format YYYY-MM-DD.")
ERR_CREATOR = _("Please fill in a value for creator.")
ERR_TITLE = _("Please fill in a value for title.")
ERR_LANGUAGE = _("Must be a valid language code (IETF BCP 47 or ISO 639-1)")
ERR_PUBLISHER = _("Please fill in a value for publisher.")
ERR_RESOURCE = _("Please choose a resource type.")
ERR_GEOPOINT_LONG = _("Needs to be decimal between -180 and 180.")
ERR_GEOPOINT_LAT = _("Needs to be decimal between -90 and 90.")
PREFIX_CREATOR_SET = 'creators-creator'
PREFIX_TITLE_SET = 'titles-title'
PREFIX_DESCR_SET = 'descriptions-description'
PREFIX_SUBJECT_SET = 'subjects-subject'
PREFIX_CONTRIB_SET = 'contributors-contributor'
PREFIX_DATE_SET = 'dates-date'
PREFIX_ALTID_SET = 'alternateIdentifiers-alternateIdentifier'
PREFIX_RELID_SET = 'relatedIdentifiers-relatedIdentifier'
PREFIX_SIZE_SET = 'sizes-size'
PREFIX_FORMAT_SET = 'formats-format'
PREFIX_RIGHTS_SET = 'rightsList-rights'
PREFIX_GEOLOC_SET = 'geoLocations-geoLocation'
PREFIX_FUNDINGREF_SET = 'fundingReferences-fundingReference'
# Translators: "e.g. " is abbreviation for "example". Please include one space at end.
ABBR_EX = _("e.g. ")

# Key/Label for nameidentifier grouping used in Creator and Contributor
NAME_ID = ["nameIdentifier_{0}-nameIdentifier", _("Name Identifier")]
NAME_ID_SCHEME = ["nameIdentifier_{0}-nameIdentifierScheme", _("Identifier Scheme")]
NAME_ID_SCHEME_URI = ["nameIdentifier_{0}-schemeURI", _("Scheme URI")]

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                   #
#               Forms for ID creation/editing                       #
#                                                                   #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

################# Basic ID Forms ####################


class BaseForm(forms.Form):
    """ Base Form object: all forms have a target field. If 'placeholder' is True
      set attribute to include specified placeholder text in text fields """

    def __init__(self, *args, **kwargs):
        self.placeholder = kwargs.pop('placeholder', None)
        super(BaseForm, self).__init__(*args, **kwargs)
        # Easier to name this field as 'target', but this is reassigned in the view as '_target'
        self.fields["target"] = forms.CharField(
            required=False, label=_("Location (URL)"), validators=[_validate_url]
        )
        if self.placeholder is not None and self.placeholder == True:
            self.fields['target'].widget.attrs['placeholder'] = _("Location (URL)")


class ErcForm(BaseForm):
    """ Form object for ID with ERC profile (Used for simple or advanced ARK).
      BaseForm parent brings in target field. If 'placeholder' is True
      set attribute to include specified placeholder text in text fields """

    def __init__(self, *args, **kwargs):
        super(ErcForm, self).__init__(*args, **kwargs)
        self.fields["erc.who"] = forms.CharField(required=False, label=_("Who"))
        self.fields["erc.what"] = forms.CharField(required=False, label=_("What"))
        self.fields["erc.when"] = forms.CharField(required=False, label=_("When"))
        if self.placeholder is not None and self.placeholder == True:
            self.fields['erc.who'].widget.attrs['placeholder'] = _("Who?")
            self.fields['erc.what'].widget.attrs['placeholder'] = _("What?")
            self.fields['erc.when'].widget.attrs['placeholder'] = _("When?")


class DcForm(BaseForm):
    """ Form object for ID with Dublin Core profile (Advanced ARK or DOI).
      BaseForm parent brings in target field. If 'placeholder' is True set
      attribute to include specified placeholder text in text fields """

    def __init__(self, *args, **kwargs):
        self.isDoi = kwargs.pop('isDoi', None)
        super(DcForm, self).__init__(*args, **kwargs)
        self.fields["dc.creator"] = forms.CharField(
            label=_("Creator"), required=True if self.isDoi else False
        )
        self.fields["dc.title"] = forms.CharField(
            label=_("Title"), required=True if self.isDoi else False
        )
        self.fields["dc.publisher"] = forms.CharField(
            label=_("Publisher"), required=True if self.isDoi else False
        )
        self.fields["dc.date"] = forms.CharField(
            label=_("Date"), required=True if self.isDoi else False
        )
        self.fields["dc.type"] = forms.CharField(required=False, label=_("Type"))


class DataciteForm(BaseForm):
    """ Form object for ID with (simple DOI) DataCite profile. BaseForm parent brings in
      target field. If 'placeholder' is True set attribute to include specified
      placeholder text in text fields """

    def __init__(self, *args, **kwargs):
        super(DataciteForm, self).__init__(*args, **kwargs)
        self.fields["datacite.creator"] = forms.CharField(
            label=_("Creator"), error_messages={'required': ERR_CREATOR}
        )
        self.fields["datacite.title"] = forms.CharField(
            label=_("Title"), error_messages={'required': ERR_TITLE}
        )
        self.fields["datacite.publisher"] = forms.CharField(
            label=_("Publisher"), error_messages={'required': ERR_PUBLISHER}
        )
        self.fields["datacite.publicationyear"] = forms.RegexField(
            label=_("Publication year"),
            regex=REGEX_4DIGITYEAR,
            error_messages={
                'required': _(
                    "Please fill in a four digit value for publication year."
                ),
                'invalid': ERR_4DIGITYEAR,
            },
        )
        self.fields["datacite.resourcetype"] = forms.ChoiceField(
            choices=RESOURCE_TYPES,
            label=_("Resource type"),
            error_messages={'required': ERR_RESOURCE},
        )
        if self.placeholder is not None and self.placeholder == True:
            self.fields['datacite.creator'].widget.attrs['placeholder'] = _(
                "Creator (required)"
            )
            self.fields['datacite.title'].widget.attrs['placeholder'] = _(
                "Title (required)"
            )
            self.fields['datacite.publisher'].widget.attrs['placeholder'] = _(
                "Publisher (required)"
            )
            self.fields['datacite.publicationyear'].widget.attrs['placeholder'] = _(
                "Publication year (required)"
            )


def getIdForm(profile, placeholder, elements=None):
    """ Returns a simple ID Django form. If 'placeholder' is True
      set attribute to include specified placeholder text in text fields """
    # Django forms does not handle field names with underscores very well
    if elements and '_target' in elements:
        elements['target'] = elements['_target']
    if profile.name == 'erc':
        form = ErcForm(elements, placeholder=placeholder, auto_id='%s')
    elif profile.name == 'datacite':
        form = DataciteForm(elements, placeholder=placeholder, auto_id='%s')
    elif profile.name == 'crossref':
        form = BaseForm(elements, placeholder=placeholder, auto_id='%s')
    elif profile.name == 'dc':
        testForDoi = None  # dc.creator is only required when creating a DOI
        form = DcForm(elements, placeholder=placeholder, isDoi=testForDoi, auto_id='%s')
    return form


################# Advanced ID Form Retrieval ###########################
### (two forms technically: RemainderForm and Profile Specific Form) ###


class RemainderForm(forms.Form):
    """ Remainder Form object: all advanced forms have a remainder field,
      validation of which requires passing in the shoulder """

    def __init__(self, *args, **kwargs):
        self.shoulder = kwargs.pop('shoulder', None)
        super(RemainderForm, self).__init__(*args, **kwargs)
        self.fields["remainder"] = forms.CharField(
            required=False,
            label=_("Custom Remainder"),
            initial=REMAINDER_BOX_DEFAULT,
            validators=[_validate_custom_remainder(self.shoulder)],
        )


def getAdvancedIdForm(profile, request=None):
    """ For advanced ID (but not datacite_xml). Returns two forms: One w/a
      single remainder field and one with profile-specific fields """
    P = shoulder = isDoi = None
    if request:
        if request.method == 'POST':
            P = request.POST
            shoulder = P['shoulder']
            isDoi = shoulder.startswith("doi:")
        elif request.method == 'GET':
            if 'shoulder' in request.GET:
                shoulder = request.GET['shoulder']
                isDoi = shoulder.startswith("doi:")
    remainder_form = RemainderForm(P, shoulder=shoulder, auto_id='%s')
    if profile.name == 'erc':
        form = ErcForm(P, auto_id='%s')
    elif profile.name == 'datacite':
        form = DataciteForm(P, auto_id='%s')
    elif profile.name == 'dc':
        form = DcForm(P, isDoi=isDoi, auto_id='%s')
    return {'remainder_form': remainder_form, 'form': form}


################# Form Validation functions  #################


def _validate_phone(p):
    r = re.sub(r'[^\d]', '', p)
    if len(r) < 8:
        raise ValidationError(_("Please enter a valid phone number, minimum 8 digits."))


def _validate_url(url):
    """ Borrowed from impl/ezid.py """
    t = url.strip()
    if t != "":
        try:
            assert len(t) <= 2000
            django.core.validators.URLValidator()(t)
        except:
            raise ValidationError(_("Please enter a valid location (URL)"))


def _validate_custom_remainder(shoulder):
    def innerfn(remainder_to_test):
        test = "" if remainder_to_test == REMAINDER_BOX_DEFAULT else remainder_to_test
        if not (util.validateIdentifier(shoulder + test)):
            raise ValidationError(
                _("This combination of characters cannot be used as a remainder.")
            )

    return innerfn


def _validateNameIdGrouping(suffix, ni, ni_s, ni_s_uri):
    err = {}
    if ni and not ni_s:
        err['nameIdentifier_{0}-nameIdentifierScheme'.format(suffix)] = _(
            "An Identifier Scheme must be filled in if you specify an Identifier."
        )
    if ni_s and not ni:
        err['nameIdentifier_{0}-nameIdentifier'.format(suffix)] = _(
            "An Identifier must be filled in if you specify an Identifier Scheme."
        )
    if ni_s_uri:
        if not ni:
            err['nameIdentifier_{0}-nameIdentifier'.format(suffix)] = _(
                "An Identifier must be filled in if you specify a Scheme URI."
            )
        if not ni_s:
            err['nameIdentifier_{0}-nameIdentifierScheme'.format(suffix)] = _(
                "An Identifier Scheme must be filled in."
            )
    return err


def _validate_geolong(n):
    m = re.match(REGEX_GEOPOINT, n)
    if not m or float(n) < -180 or float(n) > 180:
        raise ValidationError(ERR_GEOPOINT_LONG)


def _validate_geolat(n):
    m = re.match(REGEX_GEOPOINT, n)
    if not m or float(n) < -90 or float(n) > 90:
        raise ValidationError(ERR_GEOPOINT_LAT)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
################# Advanced Datacite ID Form/Elements #################

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# Element attributes must be named as elementName-attributeName
# i.e. <awardNumber awardURI="http://cordis.europa.eu/">284382</awardNumber>
#  should be declared as indiv. form fields named 'awardNumber' and 'awardNumber-awardURI'
# See datacite_xml.formElementsToDataciteXml
#
# Note that fields with hyphens cannot be called directly from the template, and so have
#   been relegated to their own form object (defined in __init__)
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


class NonRepeatingForm(forms.Form):
    """ Form object for single field elements in DataCite Advanced (XML) profile """

    target = forms.CharField(
        required=False, label=_("Location (URL)"), validators=[_validate_url]
    )
    publisher = forms.CharField(
        label=_("Publisher"), error_messages={'required': ERR_PUBLISHER}
    )
    publicationYear = forms.RegexField(
        label=_("Publication Year"),
        regex=REGEX_4DIGITYEAR,
        error_messages={
            'required': _("Please fill in a four digit value for publication year."),
            'invalid': ERR_4DIGITYEAR,
        },
    )
    language = forms.CharField(required=False, label=_("Language"))
    version = forms.CharField(required=False, label=_("Version"))


class ResourceTypeForm(forms.Form):
    """ Form object for Resource Type Element in DataCite Advanced (XML) profile """

    def __init__(self, *args, **kwargs):
        super(ResourceTypeForm, self).__init__(*args, **kwargs)
        self.fields['resourceType-resourceTypeGeneral'] = forms.ChoiceField(
            choices=RESOURCE_TYPES,
            label=_("Resource Type General"),
            error_messages={'required': ERR_RESOURCE},
        )
        self.fields['resourceType'] = forms.CharField(
            required=False, label=_("Resource Type")
        )


# Django faulty design: First formset allows blank form fields.
# http://stackoverflow.com/questions/2406537/django-formsets-make-first-required
class RequiredFormSet(BaseFormSet):
    """ Sets first form in a formset required. Used for TitleSet. """

    def __init__(self, *args, **kwargs):
        super(RequiredFormSet, self).__init__(*args, **kwargs)
        self.forms[0].empty_permitted = False


class NameIdMultBaseFormSet(BaseFormSet):
    """
  Generates aribitrary number of NameID fields. Used by Creator and Contributor formsets.
  UI only offers 2 nameIds during initial ID creation, whereas unlimited # can be generated through API.
  (Unlimited number of nameId fields *can* be displayed in UI)
  """

    def __init__(self, *args, **kwargs):
        self.nameIdLastIndex = kwargs.pop("nameIdLastIndex")
        super(NameIdMultBaseFormSet, self).__init__(*args, **kwargs)
        if self.form.__name__ == 'CreatorForm':
            self.forms[0].empty_permitted = False

    # Additional fields generated (and Affiliation field must follow Name Identifier triad)
    def _construct_form(self, i, **kwargs):
        form = super(NameIdMultBaseFormSet, self)._construct_form(i, **kwargs)
        if self.nameIdLastIndex:
            for d in self.generateNameIdFields(self.nameIdLastIndex[i]):
                k, v = d.items()[0]
                form.fields[k] = forms.CharField(required=False, label=v)
        form.fields["affiliation"] = forms.CharField(
            required=False, label=_("Affiliation")
        )
        return form

    def generateNameIdFields(self, x):
        r = []
        for n in range(0, x + 1):
            r.extend(
                [
                    {NAME_ID[0].format(str(n)): NAME_ID[1]},
                    {NAME_ID_SCHEME[0].format(str(n)): NAME_ID_SCHEME[1]},
                    {NAME_ID_SCHEME_URI[0].format(str(n)): NAME_ID_SCHEME_URI[1]},
                ]
            )
        return r


# Remaining Datacite Forms listed below are intended to be wrapped into FormSets (repeatable)
class CreatorForm(forms.Form):
    """ Form object for Creator Element in DataCite Advanced (XML) profile.
      This gets wrapped into a NameIdMultBaseFormSet (when passed into formset_factory).
  """

    def __init__(self, *args, **kwargs):
        super(CreatorForm, self).__init__(*args, **kwargs)
        self.fields["creatorName"] = forms.CharField(
            label=_("Name"),
            error_messages={'required': _("Please fill in a value for creator name.")},
        )
        self.fields["familyName"] = forms.CharField(
            required=False, label=_("Family Name")
        )
        self.fields["givenName"] = forms.CharField(
            required=False, label=_("Given Name")
        )
        # Wait, there's more: Min 2-n # of NameIdentifier fields are generated by NameIdMultBaseFormSet class
        # Affiliation field is added last in sequence within same method

    def clean(self):
        cleaned_data = super(CreatorForm, self).clean()
        errs = {}
        for i in range(0, len(self.fields) / 3 - 1):
            ni = cleaned_data.get(NAME_ID[0].format(str(i)))
            ni_s = cleaned_data.get(NAME_ID_SCHEME[0].format(str(i)))
            ni_s_uri = cleaned_data.get(NAME_ID_SCHEME_URI[0].format(str(i)))
            err = _validateNameIdGrouping(i, ni, ni_s, ni_s_uri)
            if err:
                errs.update(err.items())
        if errs:
            raise ValidationError(errs)
        return cleaned_data


class TitleForm(forms.Form):
    """ Form object for Title Element in DataCite Advanced (XML) profile """

    def __init__(self, *args, **kwargs):
        super(TitleForm, self).__init__(*args, **kwargs)
        self.fields["title"] = forms.CharField(
            label=_("Title"), error_messages={'required': ERR_TITLE}
        )
        TITLE_TYPES = (
            ("", _("Main title")),
            ("AlternativeTitle", _("Alternative title")),
            ("Subtitle", _("Subtitle")),
            ("TranslatedTitle", _("Translated title")),
            ("Other", _("Other")),
        )
        self.fields["titleType"] = forms.ChoiceField(
            required=False,
            label=_("Type"),
            widget=forms.RadioSelect(attrs={'class': 'fcontrol__radio-button-stacked'}),
            choices=TITLE_TYPES,
        )
        self.fields["{http://www.w3.org/XML/1998/namespace}lang"] = forms.RegexField(
            required=False,
            label=_("Title Language"),
            regex=REGEX_LANGUAGE,
            error_messages={'invalid': ERR_LANGUAGE},
        )


class DescrForm(forms.Form):
    """ Form object for Description Element in DataCite Advanced (XML) profile """

    def __init__(self, *args, **kwargs):
        super(DescrForm, self).__init__(*args, **kwargs)
        self.fields["description"] = forms.CharField(
            required=False,
            label=_("Descriptive information"),
            widget=forms.Textarea(attrs={'rows': '3'}),
        )
        DESCR_TYPES = (
            ("", _("Select a type of description")),
            ("Abstract", _("Abstract")),
            ("SeriesInformation", _("Series Information")),
            ("TableOfContents", _("Table of Contents")),
            ("TechnicalInfo", _("Technical Info")),
            ("Methods", _("Methods")),
            ("Other", _("Other")),
        )
        self.fields["descriptionType"] = forms.ChoiceField(
            required=False, label=_("Type"), choices=DESCR_TYPES
        )
        self.fields["{http://www.w3.org/XML/1998/namespace}lang"] = forms.RegexField(
            required=False,
            label=_("Description Language"),
            regex=REGEX_LANGUAGE,
            error_messages={'invalid': ERR_LANGUAGE},
        )

    def clean(self):
        cleaned_data = super(DescrForm, self).clean()
        d = cleaned_data.get("description")
        dt = cleaned_data.get("descriptionType")
        dl = cleaned_data.get("{http://www.w3.org/XML/1998/namespace}lang")
        if (d != '' or dl != '') and dt == '':
            raise ValidationError(
                {
                    'descriptionType': _(
                        "Description type is required if you fill in Descriptive info."
                    )
                }
            )
        return cleaned_data


class SubjectForm(forms.Form):
    """ Form object for Subject Element in DataCite Advanced (XML) profile """

    def __init__(self, *args, **kwargs):
        super(SubjectForm, self).__init__(*args, **kwargs)
        self.fields["subject"] = forms.CharField(required=False, label=_("Subject"))
        self.fields["subjectScheme"] = forms.CharField(
            required=False, label=_("Subject Scheme")
        )
        self.fields["schemeURI"] = forms.CharField(
            required=False, label=_("Scheme URI")
        )
        self.fields["valueURI"] = forms.CharField(required=False, label=_("Value URI"))
        self.fields["{http://www.w3.org/XML/1998/namespace}lang"] = forms.RegexField(
            required=False,
            label=_("Subject Language"),
            regex=REGEX_LANGUAGE,
            error_messages={'invalid': ERR_LANGUAGE},
        )


def _gatherContribErr1(err1, ctype, cname):
    if not ctype:
        err1['contributorType'] = _(
            "Type is required if you fill in contributor information."
        )
    if not cname:
        err1['contributorName'] = _(
            "Name is required if you fill in contributor information."
        )
    return err1


class ContribForm(forms.Form):
    """ Form object for Contributor Element in DataCite Advanced (XML) profile
      With specific validation rules. This gets wrapped into a NameIdMultBaseFormSet
      (when passed into formset_factory).
  """

    def __init__(self, *args, **kwargs):
        super(ContribForm, self).__init__(*args, **kwargs)
        CONTRIB_TYPES = (
            ("", _("Select a type of contributor")),
            ("ContactPerson", _("Contact Person")),
            ("DataCollector", _("Data Collector")),
            ("DataCurator", _("Data Curator")),
            ("DataManager", _("Data Manager")),
            ("Distributor", _("Distributor")),
            ("Editor", _("Editor")),
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
            ("Other", _("Other")),
        )
        self.fields["contributorType"] = forms.ChoiceField(
            required=False, label=_("Contributor Type"), choices=CONTRIB_TYPES
        )
        self.fields["contributorName"] = forms.CharField(
            required=False, label=_("Name")
        )
        self.fields["familyName"] = forms.CharField(
            required=False, label=_("Family Name")
        )
        self.fields["givenName"] = forms.CharField(
            required=False, label=_("Given Name")
        )
        # Wait, there's more: Min 2-n # of NameIdentifier fields are generated by NameIdMultBaseFormSet class
        # Affiliation field is added last in sequence within same method

    def clean(self):
        cleaned_data = super(ContribForm, self).clean()
        ctype = cleaned_data.get("contributorType")
        cname = cleaned_data.get("contributorName")
        cfname = cleaned_data.get("familyName")
        cgname = cleaned_data.get("givenName")
        err1, err2 = {}, {}
        for i in range(0, len(self.fields) / 3 - 1):
            ni = cleaned_data.get(NAME_ID[0].format(str(i)))
            ni_s = cleaned_data.get(NAME_ID_SCHEME[0].format(str(i)))
            ni_s_uri = cleaned_data.get(NAME_ID_SCHEME_URI[0].format(str(i)))
            caff = cleaned_data.get("affiliation")
            """ Use of contributor element requires name and type be populated """
            if ctype or cname or cfname or cgname or caff or ni or ni_s or ni_s_uri:
                err1 = _gatherContribErr1(err1, ctype, cname)
            err = _validateNameIdGrouping(i, ni, ni_s, ni_s_uri)
            if err:
                err2.update(err.items())
        errs = dict(err1.items() + err2.items())
        if errs:
            raise ValidationError(errs)
        return cleaned_data


class DateForm(forms.Form):
    """ Form object for Date Element in DataCite Advanced (XML) profile """

    date = forms.CharField(required=False, label=_("Date"))
    DATE_TYPES = (
        ("", _("Select a type of date")),
        ("Accepted", _("Accepted")),
        ("Available", _("Available")),
        ("Collected", _("Collected")),
        ("Copyrighted", _("Copyrighted")),
        ("Created", _("Created")),
        ("Issued", _("Issued")),
        ("Submitted", _("Submitted")),
        ("Updated", _("Updated")),
        ("Valid", _("Valid")),
    )
    dateType = forms.ChoiceField(required=False, label=_("Type"), choices=DATE_TYPES)


class AltIdForm(forms.Form):
    """ Form object for Alternate ID Element in DataCite Advanced (XML) profile """

    alternateIdentifier = forms.CharField(required=False, label=_("Identifier"))
    alternateIdentifierType = forms.CharField(
        required=False, label=_("Identifier Type")
    )

    def clean(self):
        cleaned_data = super(AltIdForm, self).clean()
        a_c = cleaned_data.get("alternateIdentifier")
        at_c = cleaned_data.get("alternateIdentifierType")
        if a_c == '' and at_c != '':
            raise ValidationError(
                {
                    'alternateIdentifier': _(
                        "Identifier is required if you fill in identifier type information."
                    )
                }
            )
        if a_c != '' and at_c == '':
            raise ValidationError(
                {
                    'alternateIdentifierType': _(
                        "Identifier Type is required if you fill in identifier information."
                    )
                }
            )
        return cleaned_data


class RelIdForm(forms.Form):
    """ Form object for Related ID Element in DataCite Advanced (XML) profile
      With specific validation rules
  """

    relatedIdentifier = forms.CharField(required=False, label=_("Identifier"))
    ID_TYPES = (
        ("", _("Select the type of related identifier")),
        ("ARK", "ARK"),
        ("arXiv", "arXiv"),
        ("bibcode", "bibcode"),
        ("DOI", "DOI"),
        ("EAN13", "EAN13"),
        ("EISSN", "EISSN"),
        ("Handle", "Handle"),
        ("IGSN", "IGSN"),
        ("ISBN", "ISBN"),
        ("ISSN", "ISSN"),
        ("ISTC", "ISTC"),
        ("LISSN", "LISSN"),
        ("LSID", "LSID"),
        ("PMID", "PMID"),
        ("PURL", "PURL"),
        ("UPC", "UPC"),
        ("URL", "URL"),
        ("URN", "URN"),
    )
    relatedIdentifierType = forms.ChoiceField(
        required=False, label=_("Identifier Type"), choices=ID_TYPES
    )
    RELATION_TYPES = (
        (
            "",
            _(
                "Select relationship of A:resource being registered and B:related resource"
            ),
        ),
        ("Cites", _("Cites")),
        ("Compiles", _("Compiles")),
        ("Continues", _("Continues")),
        ("Documents", _("Documents")),
        ("HasMetadata", _("Has Metadata")),
        ("HasPart", _("Has Part")),
        ("IsCitedBy", _("Is Cited By")),
        ("IsCompiledBy", _("Is Compiled By")),
        ("IsContinuedBy", _("Is Continued By")),
        ("IsDocumentedBy", _("Is Documented By")),
        ("IsDerivedFrom", _("Is Derived From")),
        ("IsIdenticalTo", _("Is Identical To")),
        ("IsMetadataFor", _("Is Metadata For")),
        ("IsPartOf", _("Is Part Of")),
        ("IsNewVersionOf", _("Is New Version Of")),
        ("IsOriginalFormOf", _("Is Original Form Of")),
        ("IsPreviousVersionOf", _("Is Previous Version Of")),
        ("IsReferencedBy", _("Is Referenced By")),
        ("IsReviewedBy", _("Is Reviewed By")),
        ("IsSourceOf", _("Is Source Of")),
        ("IsSupplementedBy", _("Is Supplemented By")),
        ("IsSupplementTo", _("Is Supplement To")),
        ("IsVariantFormOf", _("Is Variant Form Of")),
        ("References", _("References")),
        ("Reviews", _("Reviews")),
    )
    relationType = forms.ChoiceField(
        required=False, label=_("Relation Type"), choices=RELATION_TYPES
    )
    relatedMetadataScheme = forms.CharField(
        required=False, label=_("Related Metadata Scheme")
    )
    schemeURI = forms.CharField(required=False, label=_("Scheme URI"))
    schemeType = forms.CharField(required=False, label=_("Scheme Type"))

    def clean(self):
        cleaned_data = super(RelIdForm, self).clean()
        ri = cleaned_data.get("relatedIdentifier")
        ri_type = cleaned_data.get("relatedIdentifierType")
        r_type = cleaned_data.get("relationType")
        rm_s = cleaned_data.get("relatedMetadataScheme")
        s_uri = cleaned_data.get("schemeURI")
        s_type = cleaned_data.get("schemeType")
        err = {}
        """ Use of RelId element requires relatedIdentifier and relatedIdentifierType be populated """
        if ri or ri_type or r_type or rm_s or s_uri or s_type:
            if not ri_type:
                err['relatedIdentifierType'] = _(
                    "Related Identifier Type is required if this property is used."
                )
            if not r_type:
                err['relationType'] = _(
                    "Relation Type is required if this property is used."
                )
        if err:
            raise ValidationError(err)
        return cleaned_data


class SizeForm(forms.Form):
    """ Form object for Size Element in DataCite Advanced (XML) profile """

    size = forms.CharField(required=False, label=_("Size"))


class FormatForm(forms.Form):
    """ Form object for Format Element in DataCite Advanced (XML) profile
      format() is a python method, so playing it safe and
      defining field using the fields dictionary of the Form class
  """

    def __init__(self, *args, **kwargs):
        super(FormatForm, self).__init__(*args, **kwargs)
        self.fields["format"] = forms.CharField(required=False, label=_("Format"))


class RightsForm(forms.Form):
    """ Form object for Rights Element in DataCite Advanced (XML) profile """

    rights = forms.CharField(required=False, label=_("Rights"))
    rightsURI = forms.CharField(required=False, label=_("Rights URI"))


class GeoLocForm(forms.Form):
    """ Form object for GeoLocation Element in DataCite Advanced (XML) profile """

    def __init__(self, *args, **kwargs):
        super(GeoLocForm, self).__init__(*args, **kwargs)
        self.fields["geoLocationPoint-pointLongitude"] = forms.CharField(
            required=False, label=_("Point Longitude"), validators=[_validate_geolong]
        )
        self.fields["geoLocationPoint-pointLatitude"] = forms.CharField(
            required=False, label=_("Point Latitude"), validators=[_validate_geolat]
        )
        self.fields["geoLocationBox-westBoundLongitude"] = forms.CharField(
            required=False,
            label=_("WestBounding Longitude"),
            validators=[_validate_geolong],
        )
        self.fields["geoLocationBox-eastBoundLongitude"] = forms.CharField(
            required=False,
            label=_("EastBounding Longitude"),
            validators=[_validate_geolong],
        )
        self.fields["geoLocationBox-southBoundLatitude"] = forms.CharField(
            required=False,
            label=_("SouthBounding Latitude"),
            validators=[_validate_geolat],
        )
        self.fields["geoLocationBox-northBoundLatitude"] = forms.CharField(
            required=False,
            label=_("NorthBounding Latitude"),
            validators=[_validate_geolat],
        )
        self.fields["geoLocationPlace"] = forms.CharField(
            required=False, label=_("Place")
        )
        self.fields["geoLocationPolygon"] = forms.CharField(
            required=False,
            label=_("Polygon"),
            widget=forms.Textarea(attrs={'rows': '4'}),
        )

    # A valid polygon is one which can be properly converted to DataCite from either
    #   KML, GeoJSON, or internal "EZID Representation"
    def clean_geoLocationPolygon(self):
        text = self.cleaned_data['geoLocationPolygon'].strip()
        if text:
            text = geometry_util.polygonToDatacite(text)
            # Warning message broadcast deferred for now (warning on ignored things like
            #    altitudes and inner polygons (holes).)
            if isinstance(text, basestring):
                raise ValidationError(text)
            else:
                text = text[0]
        return text


class FundingRefForm(forms.Form):
    """ Form object for Funding Reference Element in DataCite Advanced (XML) profile """

    def __init__(self, *args, **kwargs):
        super(FundingRefForm, self).__init__(*args, **kwargs)
        self.fields["funderName"] = forms.CharField(
            required=False, label=_("Funder Name")
        )
        self.fields["funderIdentifier"] = forms.CharField(
            required=False, label=_("Funder Identifier")
        )
        ID_TYPES = (
            ("", _("Select the type of funder identifier")),
            ("ISNI", "ISNI"),
            ("GRID", "GRID"),
            ("Crossref Funder ID", _("Crossref Funder")),
            ("Other", "Other"),
        )
        self.fields["funderIdentifier-funderIdentifierType"] = forms.ChoiceField(
            required=False, label=_("Identifier Type"), choices=ID_TYPES
        )
        self.fields["awardNumber"] = forms.CharField(
            required=False, label=_("Award Number")
        )
        self.fields["awardNumber-awardURI"] = forms.CharField(
            required=False, label=_("Award URI")
        )
        self.fields["awardTitle"] = forms.CharField(
            required=False, label=_("Award Title")
        )


def getIdForm_datacite_xml(form_coll=None, request=None):
    """ For Advanced Datacite elements
      On GET, displays 'form_coll' (named tuple) data translated from XML doc
      On POST (when editing an ID or creating a new ID), uses request.POST

      Returns all elements combined into one dict of Django forms and formsets
      Fields in Django FormSets follow this naming convention:
         prefix-#-elementName
      Thus the creatorName field in the third Creator fieldset would be named:
         creators-creator-2-creatorName                                     """
    # Initialize forms and FormSets
    remainder_form = (
        nonrepeating_form
    ) = (
        resourcetype_form
    ) = (
        creator_set
    ) = (
        title_set
    ) = (
        descr_set
    ) = (
        subject_set
    ) = (
        contrib_set
    ) = (
        date_set
    ) = (
        altid_set
    ) = (
        relid_set
    ) = size_set = format_set = rights_set = geoloc_set = fundingref_set = None
    CreatorSet = formset_factory(CreatorForm, formset=NameIdMultBaseFormSet)
    TitleSet = formset_factory(TitleForm, formset=RequiredFormSet)
    DescrSet = formset_factory(DescrForm)
    SubjectSet = formset_factory(SubjectForm)
    ContribSet = formset_factory(ContribForm, formset=NameIdMultBaseFormSet)
    DateSet = formset_factory(DateForm)
    AltIdSet = formset_factory(AltIdForm)
    RelIdSet = formset_factory(RelIdForm)
    SizeSet = formset_factory(SizeForm)
    FormatSet = formset_factory(FormatForm)
    RightsSet = formset_factory(RightsForm)
    GeoLocSet = formset_factory(GeoLocForm)
    FundingRefSet = formset_factory(FundingRefForm)
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
        creator_nameIdLastIndex = _getNameIdCt(
            P.dict() if P else None, PREFIX_CREATOR_SET
        )
        creator_set = CreatorSet(
            P,
            prefix=PREFIX_CREATOR_SET,
            auto_id='%s',
            nameIdLastIndex=creator_nameIdLastIndex,
        )
        title_set = TitleSet(P, prefix=PREFIX_TITLE_SET, auto_id='%s')
        descr_set = DescrSet(P, prefix=PREFIX_DESCR_SET, auto_id='%s')
        subject_set = SubjectSet(P, prefix=PREFIX_SUBJECT_SET, auto_id='%s')
        contrib_nameIdLastIndex = _getNameIdCt(
            P.dict() if P else None, PREFIX_CONTRIB_SET
        )
        contrib_set = ContribSet(
            P,
            prefix=PREFIX_CONTRIB_SET,
            auto_id='%s',
            nameIdLastIndex=contrib_nameIdLastIndex,
        )
        date_set = DateSet(P, prefix=PREFIX_DATE_SET, auto_id='%s')
        altid_set = AltIdSet(P, prefix=PREFIX_ALTID_SET, auto_id='%s')
        relid_set = RelIdSet(P, prefix=PREFIX_RELID_SET, auto_id='%s')
        size_set = SizeSet(P, prefix=PREFIX_SIZE_SET, auto_id='%s')
        format_set = FormatSet(P, prefix=PREFIX_FORMAT_SET, auto_id='%s')
        rights_set = RightsSet(P, prefix=PREFIX_RIGHTS_SET, auto_id='%s')
        geoloc_set = GeoLocSet(P, prefix=PREFIX_GEOLOC_SET, auto_id='%s')
        fundingref_set = FundingRefSet(P, prefix=PREFIX_FUNDINGREF_SET, auto_id='%s')
    # On Edit:GET (Convert DataCite XML dict to form)
    else:
        # Note: Remainder form only needed upon ID creation
        nonrepeating_form = NonRepeatingForm(
            form_coll.nonRepeating if hasattr(form_coll, 'nonRepeating') else None,
            auto_id='%s',
        )
        resourcetype_form = ResourceTypeForm(
            form_coll.resourceType if hasattr(form_coll, 'resourceType') else None,
            auto_id='%s',
        )
        creator_nameIdLastIndex = _getNameIdCt(
            form_coll.creators if hasattr(form_coll, 'creators') else None,
            PREFIX_CREATOR_SET,
        )
        creator_set = CreatorSet(
            _inclMgmtData(
                form_coll.creators if hasattr(form_coll, 'creators') else None,
                PREFIX_CREATOR_SET,
            ),
            prefix=PREFIX_CREATOR_SET,
            auto_id='%s',
            nameIdLastIndex=creator_nameIdLastIndex,
        )
        title_set = TitleSet(
            _inclMgmtData(
                form_coll.titles if hasattr(form_coll, 'titles') else None,
                PREFIX_TITLE_SET,
            ),
            prefix=PREFIX_TITLE_SET,
            auto_id='%s',
        )
        descr_set = DescrSet(
            _inclMgmtData(
                form_coll.descrs if hasattr(form_coll, 'descrs') else None,
                PREFIX_DESCR_SET,
            ),
            prefix=PREFIX_DESCR_SET,
            auto_id='%s',
        )
        subject_set = SubjectSet(
            _inclMgmtData(
                form_coll.subjects if hasattr(form_coll, 'subjects') else None,
                PREFIX_SUBJECT_SET,
            ),
            prefix=PREFIX_SUBJECT_SET,
            auto_id='%s',
        )
        contrib_nameIdLastIndex = _getNameIdCt(
            form_coll.contribs if hasattr(form_coll, 'contribs') else None,
            PREFIX_CONTRIB_SET,
        )
        contrib_set = ContribSet(
            _inclMgmtData(
                form_coll.contribs if hasattr(form_coll, 'contribs') else None,
                PREFIX_CONTRIB_SET,
            ),
            prefix=PREFIX_CONTRIB_SET,
            auto_id='%s',
            nameIdLastIndex=contrib_nameIdLastIndex,
        )
        date_set = DateSet(
            _inclMgmtData(
                form_coll.dates if hasattr(form_coll, 'dates') else None,
                PREFIX_DATE_SET,
            ),
            prefix=PREFIX_DATE_SET,
            auto_id='%s',
        )
        altid_set = AltIdSet(
            _inclMgmtData(
                form_coll.altids if hasattr(form_coll, 'altids') else None,
                PREFIX_ALTID_SET,
            ),
            prefix=PREFIX_ALTID_SET,
            auto_id='%s',
        )
        relid_set = RelIdSet(
            _inclMgmtData(
                form_coll.relids if hasattr(form_coll, 'relids') else None,
                PREFIX_RELID_SET,
            ),
            prefix=PREFIX_RELID_SET,
            auto_id='%s',
        )
        size_set = SizeSet(
            _inclMgmtData(
                form_coll.sizes if hasattr(form_coll, 'sizes') else None,
                PREFIX_SIZE_SET,
            ),
            prefix=PREFIX_SIZE_SET,
            auto_id='%s',
        )
        format_set = FormatSet(
            _inclMgmtData(
                form_coll.formats if hasattr(form_coll, 'formats') else None,
                PREFIX_FORMAT_SET,
            ),
            prefix=PREFIX_FORMAT_SET,
            auto_id='%s',
        )
        rights_set = RightsSet(
            _inclMgmtData(
                form_coll.rights if hasattr(form_coll, 'rights') else None,
                PREFIX_RIGHTS_SET,
            ),
            prefix=PREFIX_RIGHTS_SET,
            auto_id='%s',
        )
        geoloc_set = GeoLocSet(
            _inclMgmtData(
                form_coll.geoLocations if hasattr(form_coll, 'geoLocations') else None,
                PREFIX_GEOLOC_SET,
            ),
            prefix=PREFIX_GEOLOC_SET,
            auto_id='%s',
        )
        fundingref_set = FundingRefSet(
            _inclMgmtData(
                form_coll.fundingReferences
                if hasattr(form_coll, 'fundingReferences')
                else None,
                PREFIX_FUNDINGREF_SET,
            ),
            prefix=PREFIX_FUNDINGREF_SET,
            auto_id='%s',
        )
    return {
        'remainder_form': remainder_form,
        'nonrepeating_form': nonrepeating_form,
        'resourcetype_form': resourcetype_form,
        'creator_set': creator_set,
        'title_set': title_set,
        'descr_set': descr_set,
        'subject_set': subject_set,
        'contrib_set': contrib_set,
        'date_set': date_set,
        'altid_set': altid_set,
        'relid_set': relid_set,
        'size_set': size_set,
        'format_set': format_set,
        'rights_set': rights_set,
        'geoloc_set': geoloc_set,
        'fundingref_set': fundingref_set,
    }


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
            i = int(s) + 1  # First form is numbered '0', so add 1 for actual count
            if i > i_total:
                i_total = i
    else:
        fields = {}
        i_total = (
            1  # Assume a form needs to be produced even if no data is being passed in
        )
    fields[prefix + "-TOTAL_FORMS"] = str(i_total)
    fields[prefix + "-INITIAL_FORMS"] = str(i_total)
    fields[prefix + "-MAX_NUM_FORMS"] = '1000'
    fields[prefix + "-MIN_NUM_FORMS"] = '0'
    return fields


def _getNameIdCt(fields, prefix):
    """ Tally number of nameIdentifier fields per form
      Only to be used for formsets with syntax <prefix>-#-<field>

      e.g. Second creator form has three nameId fields:
            creators-creator-1-nameIdentifier_0, creators-creator-1-nameIdentifier_1,
            creators-creator-1-nameIdentifier_2

      Returns array of integers representing last index used for each form 0 - n
  """
    r = [(0, 1)]  # Default one form with two nameIds (when first creating an ID)
    d = {}
    if fields:
        r1 = re.escape(prefix) + "-(\d+)"
        r2 = r1 + "-nameIdentifier_(\d+)"
        for f in sorted(fields.iterkeys()):
            nameIdCt = 1  # Each form should by default have 2 nameIds
            m = re.match(r1, f)
            if m:
                form = int(m.group(1))
                m = re.match(r2, f)
                if m:
                    nameIdCt = int(m.group(2))
                d[form] = (
                    nameIdCt
                    if (form not in d) or (form in d and d[form] < nameIdCt)
                    else d[form]
                )
    y = map(lambda x: x[1], d.items() if d else r)
    return y


def isValidDataciteXmlForm(form):
    """ Validate all forms and formsets included. Just pass empty or unbound form objects.
      Returns false if one or more items don't validate
  """
    numFailed = 0
    for f, v in form.iteritems():
        if v is None:
            r = True
        else:
            r = True if not v.is_bound else v.is_valid()
        if not r:
            numFailed += 1
    return numFailed == 0


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#                                                                   #
#        Remaining Forms (not related to ID creation/editing)       #
#                                                                   #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

################# User Form Validation functions  #################

# ToDo: This is not working. turned off for now.
def _validate_proxies(user):
    def innerfn(proxies):
        p_list = [p.strip() for p in proxies.split(',')]
        for proxy in p_list:
            u = ezidapp.models.getUserByUsername(proxy)
            if u == None or u == user or u.isAnonymous:
                raise ValidationError(
                    _("Unable to assign this username as proxy: \"") + proxy + "\"."
                )


def _validate_current_pw(username):
    def innerfn(pwcurrent):
        auth = userauth.authenticate(username, pwcurrent)
        if type(auth) is str or not auth:
            raise ValidationError(_("Your current password is incorrect."))

    return innerfn


################# User (My Account) Form  #################


class BasePasswordForm(forms.Form):
    """ Base Password Form object: used for Password Reset as well as for Account Settings """

    def __init__(self, *args, **kwargs):
        self.username = kwargs.pop('username', None)
        pw_reqd = kwargs.pop('pw_reqd', None)
        super(BasePasswordForm, self).__init__(*args, **kwargs)
        self.fields["pwnew"] = forms.CharField(
            required=pw_reqd, label=_("New Password"), widget=forms.PasswordInput()
        )
        self.fields["pwconfirm"] = forms.CharField(
            required=pw_reqd,
            label=_("Confirm New Password"),
            widget=forms.PasswordInput(),
        )

    def clean(self):
        cleaned_data = super(BasePasswordForm, self).clean()
        pwnew_c = cleaned_data.get("pwnew")
        pwconfirm_c = cleaned_data.get("pwconfirm")
        if pwnew_c and pwnew_c != pwconfirm_c:
            raise ValidationError(
                {'pwnew': _("Password and confirmation do not match")}
            )
        return cleaned_data


class UserForm(BasePasswordForm):
    """ Form object for My Account Page (User editing) """

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields["primaryContactName"] = forms.CharField(
            label=_("Primary Contact Name"),
            error_messages={
                'required': _("Please fill in the full name for the primary contact.")
            },
        )
        self.fields["primaryContactEmail"] = forms.EmailField(
            label=_("Primary Contact Email"),
            error_messages={
                'required': _("Please fill in your email."),
                'invalid': _("Please fill in a valid email address."),
            },
        )
        self.fields["primaryContactPhone"] = forms.CharField(
            label=_("Primary Contact Phone"),
            validators=[_validate_phone],
            error_messages={
                'required': _(
                    "Please fill in the phone number for the primary contact."
                )
            },
        )
        self.fields["secondaryContactName"] = forms.CharField(
            required=False, label=_("Secondary Contact Name")
        )
        self.fields["secondaryContactEmail"] = forms.EmailField(
            required=False,
            label=_("Secondary Contact Email"),
            error_messages={'invalid': _("Please fill in a valid email address.")},
        )
        self.fields["secondaryContactPhone"] = forms.CharField(
            required=False,
            label=_("Secondary Contact Phone"),
            validators=[_validate_phone],
        )

        self.fields["accountDisplayName"] = forms.CharField(
            label=_("Account Display Name"),
            error_messages={
                'required': _(
                    "Please fill in the name as it should be displayed for the account."
                )
            },
        )
        self.fields["accountEmail"] = forms.EmailField(
            label=_("Account Email"),
            error_messages={'required': _("Please fill in the email for the account.")},
        )
        self.fields["proxy_users_picked"] = forms.CharField(
            required=False,
            label=_("Proxy User(s)"),
            widget=forms.Textarea(attrs={'readonly': 'readonly'}),
        )
        # validators=[_validate_proxies(self.user)])
        self.fields["pwcurrent"] = forms.CharField(
            required=False,
            label=_("Current Password"),
            widget=forms.PasswordInput(),
            validators=[_validate_current_pw(self.username)],
        )

    # Not working, using template instead
    # def clean(self):
    #  cleaned_data = super(UserForm, self).clean()
    #  if cleaned_data.get("proxy_users_picked") == '':
    #    cleaned_data["proxy_users_picked"] = _("None Chosen")
    #  return cleaned_data


################# Search ID Form  #################


class BaseSearchIdForm(forms.Form):
    """ Base form object used for public Search ID page,
      and extended for use with Manage ID page        """

    keywords = forms.CharField(
        required=False,
        label=_("Search Terms"),
        widget=forms.TextInput(
            attrs={
                'placeholder': _(
                    "Full text search using words about or describing the identifier."
                )
            }
        ),
    )
    # ToDo: Determine proper regex for identifier for validation purposes
    identifier = forms.CharField(
        required=False,
        label=_("Identifier/Identifier Prefix"),
        widget=forms.TextInput(
            attrs={'placeholder': ABBR_EX + "doi:10.17605/OSF.IO/QXUPF"}
        ),
    )
    title = forms.CharField(
        required=False,
        label=_("Object Title (What)"),
        widget=forms.TextInput(
            attrs={'placeholder': ABBR_EX + "Welfare: current vs. never"}
        ),
    )
    creator = forms.CharField(
        required=False,
        label=_("Object Creator (Who)"),
        widget=forms.TextInput(
            attrs={'placeholder': ABBR_EX + _("Schofield, Timothy")}
        ),
    )
    publisher = forms.CharField(
        required=False,
        label=_("Object Publisher"),
        widget=forms.TextInput(
            attrs={'placeholder': ABBR_EX + _("Open Science Framework")}
        ),
    )
    pubyear_from = forms.RegexField(
        required=False,
        label=_("From"),
        regex='^\d{4}$',
        error_messages={'invalid': ERR_4DIGITYEAR},
        widget=forms.TextInput(attrs={'placeholder': ABBR_EX + "2015"}),
    )
    pubyear_to = forms.RegexField(
        required=False,
        label=_("To"),
        regex='^\d{4}$',
        error_messages={'invalid': ERR_4DIGITYEAR},
        widget=forms.TextInput(attrs={'placeholder': ABBR_EX + "2016"}),
    )
    object_type = forms.ChoiceField(
        required=False, choices=RESOURCE_TYPES, label=_("Object Type")
    )
    ID_TYPES = (
        ('', _("Select a type of identifier (ARK or DOI)")),
        ('ark', "ARK"),
        ('doi', "DOI"),
    )
    id_type = forms.ChoiceField(required=False, choices=ID_TYPES, label=_("ID Type"))

    def clean(self):
        """ Invalid if all fields are empty """
        field_count = len(self.fields)
        cleaned_data = super(BaseSearchIdForm, self).clean()
        """ cleaned_data contains all valid fields. So if one or more fields
        are invalid, simply bypass this check for non-empty fields"""
        if len(cleaned_data) < field_count:
            return cleaned_data
        form_empty = True
        for k, v in cleaned_data.iteritems():
            # Check for None or '', so IntegerFields with 0 or similar things don't seem empty.
            if not isinstance(v, bool):
                cleaned_data[k] = cleaned_data[k].strip()
                if not uic.isEmptyStr(v):
                    form_empty = False
        # In manage page case, just output all owners IDs - no need to throw validation error
        if form_empty and type(self).__name__ != 'ManageSearchIdForm':
            raise forms.ValidationError(
                _("Please enter information in at least one field.")
            )
        return cleaned_data


class ManageSearchIdForm(BaseSearchIdForm):
    """ Used for Searching on Manage ID page. Inherits from BaseSearchIdForm """

    target = forms.CharField(
        required=False,
        label=_("Target URL"),
        widget=forms.TextInput(
            attrs={
                'placeholder': ABBR_EX
                + "http://pqr.pitt.edu/mol/KQSWENSZQKJHSQ-SCSAIBSYSA-N"
            }
        ),
    )
    create_time_from = forms.RegexField(
        required=False,
        label=_("From"),
        regex='^\d{4}-\d{2}-\d{2}$',
        error_messages={'invalid': ERR_DATE},
        widget=forms.TextInput(attrs={'placeholder': ABBR_EX + "2016-03-30"}),
    )
    create_time_to = forms.RegexField(
        required=False,
        label=_("To"),
        regex='^\d{4}-\d{2}-\d{2}$',
        error_messages={'invalid': ERR_DATE},
        widget=forms.TextInput(attrs={'placeholder': ABBR_EX + "2016-04-29"}),
    )
    update_time_from = forms.RegexField(
        required=False,
        label=_("From"),
        regex='^\d{4}-\d{2}-\d{2}$',
        error_messages={'invalid': ERR_DATE},
        widget=forms.TextInput(attrs={'placeholder': ABBR_EX + "2016-03-30"}),
    )
    update_time_to = forms.RegexField(
        required=False,
        label=_("To"),
        regex='^\d{4}-\d{2}-\d{2}$',
        error_messages={'invalid': ERR_DATE},
        widget=forms.TextInput(attrs={'placeholder': ABBR_EX + "2016-04-29"}),
    )
    ID_STATUS = (
        ('', _("Select a status")),
        ('public', _("Public")),
        ('reserved', _("Reserved")),
        ('unavailable', _("Unavailable")),
    )
    id_status = forms.ChoiceField(
        required=False, choices=ID_STATUS, label=_("ID Status")
    )
    # render BooleanField as two radio buttons instead of a checkbox:
    # http://stackoverflow.com/questions/854683/django-booleanfield-as-radio-buttons
    harvesting = forms.TypedChoiceField(
        required=False,
        label=_("Allows Harvesting/Indexing?"),
        coerce=lambda x: x == True,
        empty_value=True,
        choices=((True, _('Yes')), (False, _('No'))),
        initial=True,
        widget=forms.RadioSelect(attrs={'class': 'fcontrol__radio-button-stacked'}),
    )
    hasMetadata = forms.TypedChoiceField(
        required=False,
        label=_("Has Metadata?"),
        coerce=lambda x: x == True,
        empty_value=True,
        choices=((True, _('Yes')), (False, _('No'))),
        initial=True,
        widget=forms.RadioSelect(attrs={'class': 'fcontrol__radio-button-stacked'}),
    )


################# Contact Us Form  #################


class ContactForm(forms.Form):
    """ Form object for Contact Us form """

    # Translators: These options will appear in drop-down on contact page
    def __init__(self, *args, **kwargs):
        CONTACT_REASONS = (
            ("None Entered", _("Choose One")),
            (
                "I would like to inquire about getting a new account for ARKs",
                _("I would like to inquire about getting a new account for ARKs *"),
            ),
            (
                "I have a problem or question about existing account",
                _("I have a problem or question about existing account"),
            ),
            ("Other", _("Other")),
        )
        # Translators: These options appear in drop-down on contact page
        REFERRAL_SOURCES = (
            ("", _("Choose One")),
            ("website", _("Website")),
            ("conference", _("Conference")),
            ("colleagues", _("Colleagues")),
            ("webinar", _("Webinar")),
            ("other", _("Other")),
        )
        self.localized = kwargs.pop('localized', None)
        super(ContactForm, self).__init__(*args, **kwargs)
        self.fields["contact_reason"] = forms.ChoiceField(
            required=False,
            choices=CONTACT_REASONS,
            label=_("Reason for contacting EZID"),
        )
        self.fields["your_name"] = forms.CharField(
            max_length=200,
            label=_("Your Name"),
            error_messages={'required': _("Please fill in your name")},
        )
        self.fields["email"] = forms.EmailField(
            max_length=200,
            label=_("Your Email"),
            error_messages={
                'required': _("Please fill in your email."),
                'invalid': _("Please fill in a valid email address."),
            },
        )
        self.fields["affiliation"] = forms.CharField(
            required=False, label=_("Your Institution"), max_length=200
        )
        self.fields["comment"] = forms.CharField(
            label=_("Please indicate any question or comment you may have"),
            widget=forms.Textarea(attrs={'rows': '4'}),
            error_messages={'required': _("Please fill in a question or comment.")},
        )
        self.fields["hear_about"] = forms.ChoiceField(
            required=False,
            choices=REFERRAL_SOURCES,
            label=_("How did you hear about us?"),
        )
        if self.localized == False:
            self.fields["newsletter"] = forms.BooleanField(
                required=False, label=_("Subscribe to the EZID newsletter")
            )
        self.fields["question"] = forms.CharField(
            max_length=200,
            label=_("Human test: How many drop down menus are in this form?"),
            error_messages={'required': _("Please answer the question")},
        )


################  Password Reset Landing Page ##########


class PwResetLandingForm(forms.Form):
    username = forms.CharField(
        label=_("Username"),
        error_messages={'required': _("Please fill in your username.")},
    )
    email = forms.EmailField(
        label=_("Email address"),
        error_messages={
            'required': _("Please fill in your email address."),
            'invalid': _("Please fill in a valid email address."),
        },
    )
    """ Strip any surrounding whitespace """
    # ToDo: This doesn't seem to work. It also need to be done for email.
    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        return username
