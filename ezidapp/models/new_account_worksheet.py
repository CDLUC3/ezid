# =============================================================================
#
# EZID :: ezidapp/models/new_account_worksheet.py
#
# Database model for new account worksheets.  Worksheets can be
# created and viewed through the admin interface (only).  EZID doesn't
# really do anything with them, just stores them indefinitely.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import datetime
import django.core.validators
import django.db.models

import validation

class NewAccountWorksheet (django.db.models.Model):
  # A worksheet that supports the process of creating an EZID user
  # account, and which contains requestor and contact information,
  # account configuration and setup information, and status
  # information.  As the name suggests, a worksheet is a kind of
  # working document, and as such does little in the way of
  # validation.

  requestDate = django.db.models.DateField("request date",
    default=datetime.date.today)

  # ORGANIZATION
  orgName = django.db.models.CharField("name", max_length=255,
    validators=[validation.nonEmpty])
  orgAcronym = django.db.models.CharField("acronym", max_length=255,
    blank=True)
  orgUrl = django.db.models.URLField("URL", max_length=255, blank=True,
    validators=[validation.unicodeBmpOnly])
  orgStreetAddress = django.db.models.CharField("street address",
    max_length=255, blank=True)

  # REQUESTOR
  reqName = django.db.models.CharField("name", max_length=255, blank=True)
  reqEmail = django.db.models.EmailField("email", max_length=255, blank=True,
    validators=[validation.unicodeBmpOnly])
  reqPhone = django.db.models.CharField("phone", max_length=255, blank=True)

  # PRIMARY CONTACT
  priUseRequestor = django.db.models.BooleanField("use requestor",
    default=False)
  priName = django.db.models.CharField("name", max_length=255, blank=True)
  priEmail = django.db.models.EmailField("email", max_length=255, blank=True,
    validators=[validation.unicodeBmpOnly])
  priPhone = django.db.models.CharField("phone", max_length=255, blank=True)

  # SECONDARY CONTACT
  secName = django.db.models.CharField("name", max_length=255, blank=True)
  secEmail = django.db.models.EmailField("email", max_length=255, blank=True,
    validators=[validation.unicodeBmpOnly])
  secPhone = django.db.models.CharField("phone", max_length=255, blank=True)

  # REQUEST
  reqUsername = django.db.models.CharField("requested username",
    max_length=255, blank=True)
  reqAccountEmailUsePrimary = django.db.models.BooleanField(
    "use primary contact's email", default=False)
  reqAccountEmail = django.db.models.EmailField("account email",
    max_length=255, blank=True, validators=[validation.unicodeBmpOnly])
  reqArks = django.db.models.BooleanField("ARKs", default=False)
  reqDois = django.db.models.BooleanField("DOIs", default=False)
  reqShoulders = django.db.models.CharField("requested shoulders/ branding",
    max_length=255, blank=True)
  reqCrossref = django.db.models.BooleanField("CrossRef", default=False)
  reqCrossrefEmailUseAccount = django.db.models.BooleanField(
    "use account email", default=False)
  reqCrossrefEmail = django.db.models.EmailField("CrossRef email",
    max_length=255, blank=True, validators=[validation.unicodeBmpOnly])
  reqHasExistingIdentifiers = django.db.models.BooleanField(
    "has existing identifiers", default=False)
  reqComments = django.db.models.TextField("requestor comments", blank=True)

  # SETUP
  setRealm = django.db.models.CharField("realm", max_length=255, blank=True)
  setExistingGroup = django.db.models.BooleanField("existing group",
    default=False)
  setGroupname = django.db.models.CharField("groupname", max_length=255,
    blank=True)
  setUsernameUseRequested = django.db.models.BooleanField(
    "use requested", default=False)
  setUsername = django.db.models.CharField("username", max_length=255,
    blank=True)
  setNeedShoulders = django.db.models.BooleanField("new shoulders required",
    default=False)
  setNeedMinters = django.db.models.BooleanField("minters required",
    default=False)
  setNotes = django.db.models.TextField("notes", blank=True)

  # STATUS
  staReady = django.db.models.BooleanField("request ready", default=False)
  staShouldersCreated = django.db.models.BooleanField("shoulders created",
    default=False)
  staAccountCreated = django.db.models.BooleanField("account created",
    default=False)

  def clean (self):
    self.orgName = self.orgName.strip()
    self.orgAcronym = self.orgAcronym.strip()
    self.orgUrl = self.orgUrl.strip()
    self.orgStreetAddress = self.orgStreetAddress.strip()
    self.reqName = self.reqName.strip()
    self.reqPhone = self.reqPhone.strip()
    self.priName = self.priName.strip()
    self.priPhone = self.priPhone.strip()
    self.secName = self.secName.strip()
    self.secPhone = self.secPhone.strip()
    self.reqUsername = self.reqUsername.strip()
    self.reqShoulders = self.reqShoulders.strip()
    self.reqComments = self.reqComments.strip()
    self.setRealm = self.setRealm.strip()
    self.setGroupname = self.setGroupname.strip()
    self.setUsername = self.setUsername.strip()
    self.setNotes = self.setNotes.strip()
    if self.priUseRequestor:
      self.priName = self.reqName
      self.priEmail = self.reqEmail
      self.priPhone = self.reqPhone
    if self.reqAccountEmailUsePrimary: self.reqAccountEmail = self.priEmail
    if self.reqCrossrefEmailUseAccount:
      self.reqCrossrefEmail = self.reqAccountEmail
    if self.setUsernameUseRequested: self.setUsername = self.reqUsername
    errors = {}
    if self.staReady:
      for f in ["orgUrl", "orgStreetAddress", "reqName", "reqEmail",
        "reqPhone", "priName", "priEmail", "priPhone", "reqUsername",
        "reqAccountEmail", "setRealm", "setGroupname", "setUsername"]:
        if getattr(self, f) == "": errors[f] = "This field is required."
      if not any(getattr(self, f) for f in ["reqArks", "reqDois"]):
        errors["reqArks"] = "Some type of identifier must be requested."
        errors["reqDois"] = "Some type of identifier must be requested."
      if not self.reqCrossref:
        if self.reqCrossrefEmailUseAccount:
          errors["reqCrossrefEmailUseAccount"] = "CrossRef is not checked."
        if self.reqCrossrefEmail != "":
          errors["reqCrossrefEmail"] = "CrossRef is not checked."
    else:
      if self.staShouldersCreated:
        errors["staShouldersCreated"] = "Request ready is not checked."
      if self.staAccountCreated:
        errors["staAccountCreated"] = "Request ready is not checked."
    if len(errors) > 0:
      raise django.core.validators.ValidationError(errors)

  def __unicode__ (self):
    return "%s, %s" % (self.orgName, str(self.requestDate))
