#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Database model for new account worksheets. Worksheets can be
created and viewed through the admin interface (only). EZID doesn't
really do anything with them, just stores them indefinitely.
"""

import datetime

import django.core.validators
import django.db.models

import ezidapp.models.validation


class NewAccountWorksheet(django.db.models.Model):
    # A worksheet that supports the process of creating an EZID user
    # account, and which contains requestor and contact information,
    # account configuration and setup information, and status
    # information. As the name suggests, a worksheet is a kind of
    # working document, and as such does little in the way of
    # validation.

    def clean(self):
        self.orgName = self.orgName.strip()
        self.orgAcronym = self.orgAcronym.strip()
        self.orgStreetAddress = self.orgStreetAddress.strip()
        self.reqName = self.reqName.strip()
        self.reqPhone = self.reqPhone.strip()
        self.priName = self.priName.strip()
        self.priPhone = self.priPhone.strip()
        self.secName = self.secName.strip()
        self.secPhone = self.secPhone.strip()
        self.reqComments = self.reqComments.strip()
        self.setRealm = self.setRealm.strip()
        self.setGroupname = self.setGroupname.strip()
        self.setUsername = self.setUsername.strip()
        self.setUserDisplayName = self.setUserDisplayName.strip()
        self.setShoulderDisplayName = self.setShoulderDisplayName.strip()
        self.setNotes = self.setNotes.strip()
        errors = {}
        if self.staReady:
            if not self.reqCrossref and self.reqCrossrefEmail != "":
                errors["reqCrossrefEmail"] = "Crossref is not checked."
        else:
            if self.staShouldersCreated:
                errors["staShouldersCreated"] = "Request ready is not checked."
            if self.staAccountCreated:
                errors["staAccountCreated"] = "Request ready is not checked."
        if len(errors) > 0:
            raise django.core.validators.ValidationError(errors)

    def __str__(self):
        if self.orgAcronym != "":
            o = f"{self.orgName} ({self.orgAcronym})"
        else:
            o = self.orgName
        return f"{o}, {str(self.requestDate)}"

    requestDate = django.db.models.DateField(
        "request date", default=datetime.date.today
    )

    # Organization

    orgName = django.db.models.CharField(
        "name",
        max_length=255,
        validators=[ezidapp.models.validation.nonEmpty],
        help_text="Ex: The Digital Archaeological Record",
    )
    orgAcronym = django.db.models.CharField(
        "acronym", max_length=255, blank=True, help_text="Ex: tDAR"
    )
    orgUrl = django.db.models.URLField("URL", max_length=255, blank=True)
    orgStreetAddress = django.db.models.CharField(
        "street address", max_length=255, blank=True
    )

    # Requestor
    reqName = django.db.models.CharField("name", max_length=255, blank=True)
    reqEmail = django.db.models.EmailField("email", max_length=255, blank=True)
    reqPhone = django.db.models.CharField("phone", max_length=255, blank=True)

    # Primary contact
    priName = django.db.models.CharField("name", max_length=255, blank=True)
    priEmail = django.db.models.EmailField("email", max_length=255, blank=True)
    priPhone = django.db.models.CharField("phone", max_length=255, blank=True)

    # Secondary contact
    secName = django.db.models.CharField("name", max_length=255, blank=True)
    secEmail = django.db.models.EmailField("email", max_length=255, blank=True)
    secPhone = django.db.models.CharField("phone", max_length=255, blank=True)

    accountEmail = django.db.models.EmailField(
        "account email",
        max_length=255,
        blank=True,
        help_text="Defaults to the primary contact's email.",
    )

    # Request
    reqArks = django.db.models.BooleanField("ARKs", default=False)
    reqDois = django.db.models.BooleanField("DOIs", default=False)
    reqCrossref = django.db.models.BooleanField("Crossref", default=False)
    reqCrossrefEmail = django.db.models.EmailField(
        "Crossref email", max_length=255, blank=True
    )
    reqComments = django.db.models.TextField("requestor comments", blank=True)

    # Setup
    setRealm = django.db.models.CharField("realm", max_length=255, blank=True)
    setGroupname = django.db.models.CharField("groupname", max_length=255, blank=True)
    setUsername = django.db.models.CharField("username", max_length=255, blank=True)
    setUserDisplayName = django.db.models.CharField(
        "user display name",
        max_length=255,
        blank=True,
        help_text="Defaults to the organization name.",
    )
    setShoulderDisplayName = django.db.models.CharField(
        "shoulder display name",
        max_length=255,
        blank=True,
        help_text="Defaults to the organization name.",
    )
    setNonDefaultSetup = django.db.models.BooleanField(
        "non-default setup", default=False
    )
    setNotes = django.db.models.TextField("notes", blank=True)

    # Status
    staReady = django.db.models.BooleanField("request ready", default=False)
    staShouldersCreated = django.db.models.BooleanField(
        "shoulders created", default=False
    )
    staAccountCreated = django.db.models.BooleanField("account created", default=False)
