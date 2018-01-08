# =============================================================================
#
# EZID :: ezidapp/models/store_identifier.py
#
# Database model for identifiers in the store database.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2017, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import django.core.exceptions
import django.db.models
import re

import custom_fields
import identifier
import shoulder
import store_datacenter
import store_group
import store_profile
import store_user

# Deferred imports...
"""
import util2
"""

class StoreIdentifier (identifier.Identifier):
  # An identifier as stored in the store database.

  # Foreign key declarations.  For performance we do not validate
  # foreign key references (but of course they're still checked in the
  # database).

  owner = custom_fields.NonValidatingForeignKey(store_user.StoreUser,
    blank=True, null=True, on_delete=django.db.models.PROTECT)
  ownergroup = custom_fields.NonValidatingForeignKey(store_group.StoreGroup,
    blank=True, null=True, default=None, on_delete=django.db.models.PROTECT)
  datacenter = custom_fields.NonValidatingForeignKey(
    store_datacenter.StoreDatacenter, blank=True, null=True,
    default=None, on_delete=django.db.models.PROTECT)
  profile = custom_fields.NonValidatingForeignKey(store_profile.StoreProfile,
    blank=True, null=True, default=None, on_delete=django.db.models.PROTECT)

  @property
  def defaultProfile (self):
    import util2
    return store_profile.getByLabel(util2.defaultProfile(self.identifier))

  def fromLegacy (self, d):
    # See Identifier.fromLegacy.  N.B.: computeComputedValues should
    # be called after this method to fill out the rest of the object.
    super(StoreIdentifier, self).fromLegacy(d)
    if d["_o"] != "anonymous": self.owner = store_user.getByPid(d["_o"])
    if d["_g"] != "anonymous": self.ownergroup = store_group.getByPid(d["_g"])
    self.profile = store_profile.getByLabel(d["_p"])
    if self.isDoi:
      self.datacenter = shoulder.getDatacenterBySymbol(d["_d"])

  def updateFromUntrustedLegacy (self, d, allowRestrictedSettings=False):
    # Fills out a new identifier or (partially) updates an existing
    # identifier from client-supplied (i.e., untrusted) legacy
    # metadata.  When filling out a new identifier the identifier
    # string and owner must already be set as in, for example,
    # StoreIdentifier(identifier=..., owner=...) (but note that the
    # owner may be None to signify an anonymously-owned identifier).
    # If 'allowRestrictedSettings' is True, fields and values that are
    # not ordinarily settable by clients may be set.  Throws
    # django.core.exceptions.ValidationError on all errors.
    # my_full_clean should be called after this method to fully fill
    # out and validate the object.  This method checks for state
    # transition violations, but does no permissions checking, and in
    # particular, does not check the allowability of ownership
    # changes.
    for k in d:
      if k == "_owner":
        o = store_user.getByUsername(d[k])
        if o == None or o == store_user.AnonymousUser:
          raise django.core.exceptions.ValidationError(
            { "owner": "No such user." })
        self.owner = o
        self.ownergroup = None
      elif k == "_ownergroup":
        if not allowRestrictedSettings:
          raise django.core.exceptions.ValidationError(
            { "ownergroup": "Field is not settable." })
        g = store_group.getByGroupname(d[k])
        if g == None or g == store_group.AnonymousGroup:
          raise django.core.exceptions.ValidationError(
            { "ownergoup": "No such group." })
        self.ownergroup = g
      elif k == "_created":
        if not allowRestrictedSettings:
          raise django.core.exceptions.ValidationError(
            { "createTime": "Field is not settable." })
        self.createTime = d[k]
      elif k == "_updated":
        if not allowRestrictedSettings:
          raise django.core.exceptions.ValidationError(
            { "updateTime": "Field is not settable." })
        self.updateTime = d[k]
      elif k == "_status":
        if d[k] == "reserved":
          if self.pk == None or self.isReserved or allowRestrictedSettings:
            self.status = StoreIdentifier.RESERVED
            self.unavailableReason = ""
          else:
            raise django.core.exceptions.ValidationError(
              { "status": "Invalid identifier status change." })
        elif d[k] == "public":
          self.status = StoreIdentifier.PUBLIC
          self.unavailableReason = ""
        else:
          m = re.match("unavailable(?:$| *\|(.*))", d[k])
          if m:
            if (self.pk != None and not self.isReserved) or\
              allowRestrictedSettings:
              self.status = StoreIdentifier.UNAVAILABLE
              if m.group(1) != None:
                self.unavailableReason = m.group(1)
              else:
                self.unavailableReason = ""
            else:
              raise django.core.exceptions.ValidationError(
                { "status": "Invalid identifier status change." })
          else:
            raise django.core.exceptions.ValidationError(
              { "status": "Invalid identifier status." })
      elif k == "_export":
        if d[k].lower() == "yes":
          self.exported = True
        elif d[k].lower() == "no":
          self.exported = False
        else:
          raise django.core.exceptions.ValidationError(
            { "exported": "Value must be 'yes' or 'no'." })
      elif k == "_datacenter":
        if not allowRestrictedSettings:
          raise django.core.exceptions.ValidationError(
            { "_datacenter": "Field is not settable." })
        try:
          self.datacenter = shoulder.getDatacenterBySymbol(d[k])
        except store_datacenter.StoreDatacenter.DoesNotExist:
          raise django.core.exceptions.ValidationError(
            { "datacenter": "No such datacenter." })
      elif k == "_crossref":
        if d[k].lower() == "yes":
          if self.isReserved:
            self.crossrefStatus = StoreIdentifier.CR_RESERVED
          else:
            self.crossrefStatus = StoreIdentifier.CR_WORKING
          self.crossrefMessage = ""
        elif d[k].lower() == "no":
          if self.pk == None or self.isReserved or allowRestrictedSettings:
            self.crossrefStatus = ""
            self.crossrefMessage = ""
          else:
            raise django.core.exceptions.ValidationError(
              { "crossrefStatus": "Crossref registration can be " +\
              "removed from reserved identifiers only." })
        elif allowRestrictedSettings:
          # OK, this is a hack used by the Crossref queue.
          self.crossrefStatus = d[k][0]
          self.crossrefMessage = d[k][1:]
        else:
          raise django.core.exceptions.ValidationError(
            { "crossrefStatus": "Value must be 'yes' or 'no'." })
      elif k == "_target":
        self.target = d[k]
      elif k == "_profile":
        if d[k] == "":
          self.profile = None
        else:
          try:
            self.profile = store_profile.getByLabel(d[k])
          except django.core.exceptions.ValidationError, e:
            raise django.core.exceptions.ValidationError({ "profile": [e] })
      elif k == "_ezid_role":
        if not allowRestrictedSettings:
          raise django.core.exceptions.ValidationError(
            { "_ezid_role": "Field is not settable." })
        self.agentRole = self.agentRoleDisplayToCode.get(d[k], d[k])
      elif k.startswith("_"):
        raise django.core.exceptions.ValidationError(
          { k: "Field is not settable." })
      else:
        self.cm[k] = d[k]
