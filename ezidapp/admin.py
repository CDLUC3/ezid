# =============================================================================
#
# EZID :: ezidapp/admin.py
#
# Django admin configuration/customization.  Beware: there's some
# seriously occult stuff in here, and there are dependencies on the
# specific version of Django used in development (1.8.1).  Intimately
# related to this file are the PROJECT_ROOT/templates/admin and
# PROJECT_ROOT/static/admin directories.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2016, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import copy
import django.conf
import django.contrib.admin
import django.contrib.messages
import django.core.mail
import django.core.urlresolvers
import django.core.validators
import django.db
import django.db.models
import django.forms
import django.utils.html

import models
import models.search_identifier
import models.store_group
import models.store_user
import util

# Deferred imports...
"""
import config
import ezid
import log
import ui_common
"""

class SuperuserSite (django.contrib.admin.sites.AdminSite):
  # This administrative site allows full access.
  site_header = "EZID superuser administration"
  site_title = "EZID superuser administration"
  index_title = "Administration home"
  def each_context (self, request):
    context = super(SuperuserSite, self).each_context(request)
    context["readonly_models"] = ["Shoulder", "StoreDatacenter"]
    return context

superuser = SuperuserSite()

class ServerVariablesForm (django.forms.ModelForm):
  def clean (self):
    super(ServerVariablesForm, self).clean()
    if "secretKey" in self.changed_data and\
      self.cleaned_data["secretKey"] != "":
      raise django.core.validators.ValidationError(
        { "secretKey": "The secret key can only be set to blank." })

class ServerVariablesAdmin (django.contrib.admin.ModelAdmin):
  actions = None
  fieldsets = [
    (None, { "fields": ["alertMessage"] }),
    ("Advanced", { "fields": ["secretKey"], "classes": ["collapse"] })]
  form = ServerVariablesForm
  def has_add_permission (self, request):
    return False
  def has_delete_permission (self, request, obj=None):
    return False
  def save_model (self, request, obj, form, change):
    assert change
    obj.save()
    if "alertMessage" in form.changed_data:
      import ui_common
      ui_common.alertMessage = obj.alertMessage
    if obj.secretKey == "":
      import config
      config.reload()
      django.contrib.messages.success(request, "Server reloaded.")
    return obj

superuser.register(models.ServerVariables, ServerVariablesAdmin)

class ShoulderForm (django.forms.ModelForm):
  def clean (self):
    raise django.core.validators.ValidationError(
      "Object cannot be updated using this interface.")

class ShoulderTypeFilter (django.contrib.admin.SimpleListFilter):
  title = "type"
  parameter_name = "type"
  def lookups (self, request, model_admin):
    return [(t, t) for t in ["ARK", "DOI", "UUID"]]
  def queryset (self, request, queryset):
    if self.value() != None:
      queryset = queryset.filter(prefix__startswith=self.value().lower()+":")
    return queryset

class ShoulderHasMinterFilter (django.contrib.admin.SimpleListFilter):
  title = "has minter"
  parameter_name = "hasMinter"
  def lookups (self, request, model_admin):
    return [("Yes", "Yes"), ("No", "No")]
  def queryset (self, request, queryset):
    if self.value() != None:
      if self.value() == "Yes":
        queryset = queryset.filter(~django.db.models.Q(minter=""))
      else:
        queryset = queryset.filter(minter="")
    return queryset

class ShoulderUnusedFilter (django.contrib.admin.SimpleListFilter):
  title = "is unused"
  parameter_name = "isUnused"
  def lookups (self, request, model_admin):
    return [("Yes", "Yes"), ("No", "No")]
  def queryset (self, request, queryset):
    if self.value() != None:
      if self.value() == "Yes":
        queryset = queryset.filter(storegroup__isnull=True)
      else:
        queryset = queryset.filter(storegroup__isnull=False).distinct()
    return queryset

class StoreGroupInline (django.contrib.admin.TabularInline):
  model = models.StoreGroup.shoulders.through
  verbose_name_plural = "Groups using this shoulder"
  def groupLink (self, obj):
    link = django.core.urlresolvers.reverse("admin:ezidapp_storegroup_change",
      args=[obj.storegroup.id])
    return "<a href=\"%s\">%s</a>" % (link, obj.storegroup.groupname)
  groupLink.allow_tags = True
  groupLink.short_description = "groupname"
  def organizationName (self, obj):
    return obj.storegroup.organizationName
  organizationName.short_description = "organization name"
  def realm (self, obj):
    return obj.storegroup.realm.name
  fields = ["groupLink", "organizationName", "realm"]
  readonly_fields = ["groupLink", "organizationName", "realm"]
  ordering = ["storegroup__groupname"]
  extra = 0
  def has_add_permission (self, request):
    return False
  def has_delete_permission (self, request, obj=None):
    return False

class StoreUserInlineForShoulder (django.contrib.admin.TabularInline):
  model = models.StoreUser.shoulders.through
  verbose_name_plural = "Users using this shoulder"
  def userLink (self, obj):
    link = django.core.urlresolvers.reverse("admin:ezidapp_storeuser_change",
      args=[obj.storeuser.id])
    return "<a href=\"%s\">%s</a>" % (link, obj.storeuser.username)
  userLink.allow_tags = True
  userLink.short_description = "username"
  def displayName (self, obj):
    return obj.storeuser.displayName
  displayName.short_description = "display name"
  def group (self, obj):
    return obj.storeuser.group.groupname
  fields = ["userLink", "displayName", "group"]
  readonly_fields = ["userLink", "displayName", "group"]
  ordering = ["storeuser__username"]
  extra = 0
  def has_add_permission (self, request):
    return False
  def has_delete_permission (self, request, obj=None):
    return False

class ShoulderAdmin (django.contrib.admin.ModelAdmin):
  def datacenterLink (self, obj):
    link = django.core.urlresolvers.reverse(
      "admin:ezidapp_storedatacenter_change", args=[obj.datacenter.id])
    return "<a href=\"%s\">%s</a>" % (link, obj.datacenter.symbol)
  datacenterLink.allow_tags = True
  datacenterLink.short_description = "datacenter"
  search_fields = ["prefix", "name"]
  actions = None
  list_filter = [ShoulderTypeFilter, ShoulderHasMinterFilter,
    "crossrefEnabled", ShoulderUnusedFilter]
  ordering = ["name"]
  list_display = ["prefix", "name"]
  fields = ["prefix", "name", "minter", "datacenterLink", "crossrefEnabled"]
  readonly_fields = ["prefix", "name", "minter", "datacenterLink",
    "crossrefEnabled"]
  inlines = [StoreGroupInline, StoreUserInlineForShoulder]
  form = ShoulderForm
  def has_add_permission (self, request):
    return False
  def has_delete_permission (self, request, obj=None):
    return False

superuser.register(models.Shoulder, ShoulderAdmin)

class ShoulderInline (django.contrib.admin.TabularInline):
  model = models.Shoulder
  verbose_name_plural = "Shoulders using this datacenter"
  def shoulderLink (self, obj):
    link = django.core.urlresolvers.reverse("admin:ezidapp_shoulder_change",
      args=[obj.id])
    return "<a href=\"%s\">%s</a>" % (link, obj.prefix)
  shoulderLink.allow_tags = True
  shoulderLink.short_description = "prefix"
  fields = ["shoulderLink", "name", "crossrefEnabled"]
  readonly_fields = ["shoulderLink", "name", "crossrefEnabled"]
  ordering = ["name"]
  extra = 0
  def has_add_permission (self, request):
    return False
  def has_delete_permission (self, request, obj=None):
    return False

class StoreDatacenterForm (django.forms.ModelForm):
  def clean (self):
    raise django.core.validators.ValidationError(
      "Object cannot be updated using this interface.")

class StoreDatacenterAllocatorFilter (django.contrib.admin.SimpleListFilter):
  title = "allocator"
  parameter_name = "allocator"
  def lookups (self, request, model_admin):
    allocators = set()
    for dc in models.StoreDatacenter.objects.all():
      allocators.add(dc.allocator)
    return [(a, a) for a in sorted(list(allocators))]
  def queryset (self, request, queryset):
    if self.value() != None:
      queryset = queryset.filter(symbol__startswith=self.value()+".")
    return queryset

class DatacenterUnusedFilter (django.contrib.admin.SimpleListFilter):
  title = "is unused"
  parameter_name = "isUnused"
  def lookups (self, request, model_admin):
    return [("Yes", "Yes"), ("No", "No")]
  def queryset (self, request, queryset):
    if self.value() != None:
      if self.value() == "Yes":
        queryset = queryset.filter(shoulder__isnull=True)
      else:
        queryset = queryset.filter(shoulder__isnull=False).distinct()
    return queryset

class StoreDatacenterAdmin (django.contrib.admin.ModelAdmin):
  search_fields = ["symbol", "name"]
  actions = None
  list_filter = [StoreDatacenterAllocatorFilter, DatacenterUnusedFilter]
  ordering = ["symbol"]
  list_display = ["symbol", "name"]
  readonly_fields = ["symbol", "name"]
  inlines = [ShoulderInline]
  form = StoreDatacenterForm
  def has_add_permission (self, request):
    return False
  def has_delete_permission (self, request, obj=None):
    return False

superuser.register(models.StoreDatacenter, StoreDatacenterAdmin)

class NewAccountWorksheetForm (django.forms.ModelForm):
  def __init__ (self, *args, **kwargs):
    super(NewAccountWorksheetForm, self).__init__(*args, **kwargs)
    self.fields["orgStreetAddress"].widget =\
      django.contrib.admin.widgets.AdminTextareaWidget()

class NewAccountWorksheetAdmin (django.contrib.admin.ModelAdmin):
  def organizationName (self, obj):
    if obj.orgAcronym != "":
      return "%s (%s)" % (obj.orgName, obj.orgAcronym)
    else:
      return obj.orgName
  organizationName.short_description = "organization name"
  search_fields = ["orgName", "orgAcronym", "orgStreetAddress", "reqName",
    "priName", "secName", "reqComments", "setGroupname", "setUsername",
    "setUserDisplayName", "setShoulderDisplayName", "setNotes"]
  actions = None
  list_filter = ["staReady", "staShouldersCreated", "staAccountCreated"]
  ordering = ["-requestDate", "orgName"]
  list_display = ["organizationName", "requestDate"]
  fieldsets = [
    (None, { "fields": ["requestDate"] }),
    ("Organization", { "fields": ["orgName", "orgAcronym", "orgUrl",
      "orgStreetAddress"] }),
    ("Requestor", { "fields": ["reqName", "reqEmail", "reqPhone"] }),
    ("Primary contact (defaults to requestor)", { "fields": ["priName",
      "priEmail", "priPhone"] }),
    ("Secondary contact (optional)", { "fields": ["secName", "secEmail",
      "secPhone"] }),
    (None, { "fields": ["accountEmail"] }),
    ("Request", { "fields": [("reqArks", "reqDois"), "reqCrossref",
      "reqCrossrefEmail", "reqComments"] }),
    ("Setup", { "fields": ["setRealm", "setGroupname", "setUsername",
      "setUserDisplayName", "setShoulderDisplayName", "setNonDefaultSetup",
      "setNotes"] }),
    ("Status", { "fields": ["staReady", "staShouldersCreated",
      "staAccountCreated"] })]
  form = NewAccountWorksheetForm
  def save_model (self, request, obj, form, change):
    obj.save()
    newStatus = []
    for f in ["staReady", "staShouldersCreated", "staAccountCreated"]:
      if f in form.changed_data and getattr(obj, f):
        newStatus.append(obj._meta.get_field(f).verbose_name)
    if len(newStatus) > 0:
      import config
      addresses = [a for a in\
        config.get("email.new_account_email").split(",") if len(a) > 0]
      if len(addresses) > 0:
        subject = "New account \"%s\": %s" % (str(obj), ", ".join(newStatus))
        message = ("The status of a new account request has changed.\n\n" +\
          "Organization: %s%s\n" +\
          "Request date: %s\n" +\
          "New status: %s\n\n" +\
          "View the account's worksheet at:\n\n" +\
          "%s%s\n\n" +\
          "This is an automated email.  Please do not reply.\n\n" +\
          "::\n" +\
          "organization_name: %s\n" +\
          "organization_acronym: %s\n" +\
          "organization_url: %s\n" +\
          "organization_street_address: %s\n" +\
          "requestor_name: %s\n" +\
          "requestor_email: %s\n" +\
          "requestor_phone: %s\n" +\
          "primary_contact_name: %s\n" +\
          "primary_contact_email: %s\n" +\
          "primary_contact_phone: %s\n" +\
          "secondary_contact_name: %s\n" +\
          "secondary_contact_email: %s\n" +\
          "secondary_contact_phone: %s\n" +\
          "account_email: %s\n" +\
          "arks: %s\n" +\
          "dois: %s\n" +\
          "crossref: %s\n" +\
          "crossref_email: %s\n" +\
          "requestor_comments: %s\n" +\
          "realm: %s\n" +\
          "groupname: %s\n" +\
          "username: %s\n" +\
          "user_display_name: %s\n" +\
          "shoulder_display_name: %s\n" +\
          "non_default_setup: %s\n" +\
          "setup_notes: %s\n") %\
          (obj.orgName,
          " (%s)" % obj.orgAcronym if obj.orgAcronym != "" else "",
          str(obj.requestDate), ", ".join(newStatus),
          config.get("DEFAULT.ezid_base_url"),
          django.core.urlresolvers.reverse(
          "admin:ezidapp_newaccountworksheet_change", args=[obj.id]),
          obj.orgName, obj.orgAcronym, obj.orgUrl,
          util.oneLine(obj.orgStreetAddress),
          obj.reqName, obj.reqEmail, obj.reqPhone,
          obj.priName, obj.priEmail, obj.priPhone,
          obj.secName, obj.secEmail, obj.secPhone,
          obj.accountEmail, str(obj.reqArks), str(obj.reqDois),
          str(obj.reqCrossref), obj.reqCrossrefEmail,
          util.oneLine(obj.reqComments),
          obj.setRealm, obj.setGroupname, obj.setUsername,
          obj.setUserDisplayName, obj.setShoulderDisplayName,
          str(obj.setNonDefaultSetup), util.oneLine(obj.setNotes))
        try:
          django.core.mail.send_mail(subject, message,
            django.conf.settings.SERVER_EMAIL, addresses)
        except Exception, e:
          django.contrib.messages.error(request,
            "Error sending status change email: " + str(e))
        else:
          django.contrib.messages.success(request, "Status change email sent.")

superuser.register(models.NewAccountWorksheet, NewAccountWorksheetAdmin)

class StoreRealmAdmin (django.contrib.admin.ModelAdmin):
  actions = None
  ordering = ["name"]
  def save_model (self, request, obj, form, change):
    if change:
      oldName = models.StoreRealm.objects.get(pk=obj.pk).name
      obj.save()
      models.SearchRealm.objects.filter(name=oldName).update(name=obj.name)
    else:
      sr = models.SearchRealm(name=obj.name)
      sr.full_clean()
      obj.save()
      sr.save()
  def delete_model (self, request, obj):
    obj.delete()
    models.SearchRealm.objects.filter(name=obj.name).delete()

superuser.register(models.StoreRealm, StoreRealmAdmin)

class StoreGroupRealmFilter (django.contrib.admin.RelatedFieldListFilter):
  def __new__ (cls, *args, **kwargs):
    i = django.contrib.admin.RelatedFieldListFilter.create(*args, **kwargs)
    i.title = "realm"
    return i

class StoreGroupShoulderlessFilter (django.contrib.admin.SimpleListFilter):
  title = "shoulderless"
  parameter_name = "shoulderless"
  def lookups (self, request, model_admin):
    return [("Yes", "Yes"), ("No", "No")]
  def queryset (self, request, queryset):
    if self.value() != None:
      if self.value() == "Yes":
        queryset = queryset.filter(shoulders=None)
      else:
        queryset = queryset.filter(~django.db.models.Q(shoulders=None))
    return queryset

class StoreUserInlineForGroup (django.contrib.admin.TabularInline):
  model = models.StoreUser
  verbose_name_plural = "Users in this group"
  def userLink (self, obj):
    link = django.core.urlresolvers.reverse("admin:ezidapp_storeuser_change",
      args=[obj.id])
    return "<a href=\"%s\">%s</a>" % (link, obj.username)
  userLink.allow_tags = True
  userLink.short_description = "username"
  fields = ["userLink", "displayName", "isGroupAdministrator"]
  readonly_fields = ["userLink", "displayName", "isGroupAdministrator"]
  ordering = ["username"]
  extra = 0
  def has_add_permission (self, request):
    return False
  def has_delete_permission (self, request, obj=None):
    return False

class StoreGroupForm (django.forms.ModelForm):
  def __init__ (self, *args, **kwargs):
    super(StoreGroupForm, self).__init__(*args, **kwargs)
    self.fields["organizationStreetAddress"].widget =\
      django.contrib.admin.widgets.AdminTextareaWidget()
    self.fields["shoulders"].queryset = models.Shoulder.objects.filter(
      isTest=False).order_by("name", "type")

def createOrUpdateGroupPid (request, obj, change):
  import ezid
  import log
  f = ezid.setMetadata if change else ezid.createIdentifier
  r = f(obj.pid, models.getAdminUser(),
    { "_ezid_role": "group", "_export": "no", "_profile": "ezid",
    "ezid.group.groupname": obj.groupname,
    "ezid.group.realm": obj.realm.name,
    "ezid.group.organizationName": obj.organizationName,
    "ezid.group.organizationAcronym": obj.organizationAcronym,
    "ezid.group.organizationUrl": obj.organizationUrl,
    "ezid.group.organizationStreetAddress": obj.organizationStreetAddress,
    "ezid.group.agreementOnFile": str(obj.agreementOnFile),
    "ezid.group.crossrefEnabled": str(obj.crossrefEnabled),
    "ezid.group.shoulders": " ".join(s.prefix for s in obj.shoulders.all()),
    "ezid.group.notes": obj.notes })
  if r.startswith("success:"):
    django.contrib.messages.success(request, "Group PID %s." %\
      ("updated" if change else "created"))
  else:
    log.otherError("admin.createOrUpdateGroupPid", Exception(
      "ezid.%s call failed: %s" % ("setMetadata" if change else\
      "createIdentifier", r)))
    django.contrib.messages.error(request, "Error %s group PID." %\
      ("updating" if change else "creating"))

def updateUserPids (request, users):
  import ezid
  import log
  errors = False
  for u in users:
    r = ezid.setMetadata(u.pid, models.getAdminUser(),
      { "ezid.user.shoulders": " ".join(s.prefix for s in u.shoulders.all()),
        "ezid.user.crossrefEnabled": str(u.crossrefEnabled),
        "ezid.user.crossrefEmail": u.crossrefEmail })
    if not r.startswith("success:"):
      errors = True
      log.otherError("admin.updateUserPids",
        Exception("ezid.setMetadata call failed: " + r))
  if errors:
    django.contrib.messages.error(request, "Error updating user PIDs.")
  else:
    django.contrib.messages.success(request, "User PIDs updated.")

def onCommitWithSqliteHack (onCommitFunction):
  # Oy vay, this has been so difficult to make work.  Our recursive
  # calls to EZID to create and update agent PIDs must occur in
  # on_commit hooks because the Django admin, in its infinite wisdom,
  # delays updating many-to-many relationships.  This is not a problem
  # for MySQL, but SQLite doesn't support starting a new transaction
  # in an on_commit hook... something about the autocommit setting.
  # As a hack, we force the operation to go through by setting an
  # internal Django flag.  The flag is reset afterwards for good
  # measure, though it's not clear this is necessary.  The effect of
  # this hack is probably to break transaction rollback.
  if "sqlite3" in django.conf.settings.DATABASES["default"]["ENGINE"]:
    c = django.db.connection
    v = c.features.autocommits_when_autocommit_is_off
    def setFlag (value):
      c.features.autocommits_when_autocommit_is_off = value
    django.db.connection.on_commit(lambda: setFlag(False))
    django.db.connection.on_commit(onCommitFunction)
    django.db.connection.on_commit(lambda: setFlag(v))
  else:
    django.db.connection.on_commit(onCommitFunction)

class StoreGroupAdmin (django.contrib.admin.ModelAdmin):
  def organizationNameSpelledOut (self, obj):
    return obj.organizationName
  organizationNameSpelledOut.short_description = "organization name"
  def shoulderLinks (self, obj):
    return "<br/>".join("<a href=\"%s\">%s (%s)</a>" % (
      django.core.urlresolvers.reverse("admin:ezidapp_shoulder_change",
      args=[s.id]), django.utils.html.escape(s.name), s.prefix)\
      for s in obj.shoulders.all().order_by("name", "type"))
  shoulderLinks.allow_tags = True
  shoulderLinks.short_description = "links to shoulders"
  search_fields = ["groupname", "organizationName", "organizationAcronym",
    "organizationStreetAddress", "notes"]
  actions = None
  list_filter = [("realm__name", StoreGroupRealmFilter), "accountType",
    "crossrefEnabled", StoreGroupShoulderlessFilter]
  ordering = ["groupname"]
  list_display = ["groupname", "organizationNameSpelledOut", "realm"]
  fieldsets = [
    (None, { "fields": ["pid", "groupname", "realm"] }),
    ("Organization", { "fields": ["organizationName", "organizationAcronym",
      "organizationUrl", "organizationStreetAddress"] }),
    (None, { "fields": ["accountType", "agreementOnFile", "crossrefEnabled",
      "shoulders", "shoulderLinks", "notes"] })]
  readonly_fields = ["pid", "shoulderLinks"]
  def get_readonly_fields (self, request, obj=None):
    if obj:
      return self.readonly_fields + ["realm"]
    else:
      return self.readonly_fields
  filter_vertical = ["shoulders"]
  inlines = [StoreUserInlineForGroup]
  form = StoreGroupForm
  def save_model (self, request, obj, form, change):
    clearCaches = False
    if change:
      obj.save()
      models.SearchGroup.objects.filter(pid=obj.pid).\
        update(groupname=obj.groupname)
      clearCaches = True
    else:
      sg = models.SearchGroup(pid=obj.pid, groupname=obj.groupname,
        realm=models.SearchRealm.objects.get(name=obj.realm.name))
      sg.full_clean()
      obj.save()
      sg.save()
    # Our actions won't take effect until the Django admin's
    # transaction commits sometime in the future, so we defer clearing
    # the relevant caches.  While not obvious, the following calls
    # rely on the django-transaction-hooks 3rd party package.  (Django
    # 1.9 incorporates this functionality directly.)
    if clearCaches:
      django.db.connection.on_commit(models.store_group.clearCaches)
      django.db.connection.on_commit(models.search_identifier.clearGroupCache)
    onCommitWithSqliteHack(
      lambda: createOrUpdateGroupPid(request, obj, change))
    # Changes to shoulders and Crossref enablement may trigger
    # adjustments to users in the group.
    if change:
      doUpdateUserPids = False
      # Though the group object has been saved above, its shoulder set
      # is still unchanged at this point because the Django admin app
      # performs many-to-many operations only after updating the
      # object.
      oldShoulders = obj.shoulders.all()
      newShoulders = form.cleaned_data["shoulders"]
      for s in oldShoulders:
        if s not in newShoulders:
          for u in obj.users.all(): u.shoulders.remove(s)
          doUpdateUserPids = True
      for s in newShoulders:
        if s not in oldShoulders:
          for u in obj.users.filter(inheritGroupShoulders=True):
            u.shoulders.add(s)
          doUpdateUserPids = True
      if "crossrefEnabled" in form.changed_data and not obj.crossrefEnabled:
        obj.users.all().update(crossrefEnabled=False, crossrefEmail="")
        doUpdateUserPids = True
      if doUpdateUserPids:
        django.db.connection.on_commit(models.store_user.clearCaches)
        django.db.connection.on_commit(models.search_identifier.clearUserCache)
        users = list(obj.users.all())
        onCommitWithSqliteHack(lambda: updateUserPids(request, users))
  def delete_model (self, request, obj):
    obj.delete()
    models.SearchGroup.objects.filter(pid=obj.pid).delete()
    django.contrib.messages.warning(request,
      "Now-defunct group PID %s not deleted; you may consider doing so." %\
      obj.pid)
    # See comment above.
    django.db.connection.on_commit(models.store_group.clearCaches)
    django.db.connection.on_commit(models.search_identifier.clearGroupCache)
  class Media:
    css = { "all": ["admin/css/base-group.css"] }

superuser.register(models.StoreGroup, StoreGroupAdmin)

class StoreUserRealmFilter (django.contrib.admin.RelatedFieldListFilter):
  def __new__ (cls, *args, **kwargs):
    i = django.contrib.admin.RelatedFieldListFilter.create(*args, **kwargs)
    i.title = "realm"
    return i

class StoreUserHasProxiesFilter (django.contrib.admin.SimpleListFilter):
  title = "has proxies"
  parameter_name = "hasProxies"
  def lookups (self, request, model_admin):
    return [("Yes", "Yes"), ("No", "No")]
  def queryset (self, request, queryset):
    if self.value() != None:
      if self.value() == "Yes":
        queryset = queryset.filter(~django.db.models.Q(proxies=None))
      else:
        queryset = queryset.filter(proxies=None)
    return queryset

class StoreUserIsProxyFilter (django.contrib.admin.SimpleListFilter):
  title = "is proxy"
  parameter_name = "isProxy"
  def lookups (self, request, model_admin):
    return [("Yes", "Yes"), ("No", "No")]
  def queryset (self, request, queryset):
    if self.value() != None:
      if self.value() == "Yes":
        queryset = queryset.filter(storeuser__isnull=False).distinct()
      else:
        queryset = queryset.filter(storeuser__isnull=True)
    return queryset

class StoreUserAdministratorFilter (django.contrib.admin.SimpleListFilter):
  title = "is administrator"
  parameter_name = "administrator"
  def lookups (self, request, model_admin):
    return [("No", "No"), ("Group", "Group"), ("Realm", "Realm")]
  def queryset (self, request, queryset):
    if self.value() != None:
      if self.value() == "No":
        queryset = queryset.filter(isGroupAdministrator=False)\
          .filter(isRealmAdministrator=False).filter(isSuperuser=False)
      elif self.value() == "Group":
        queryset = queryset.filter(isGroupAdministrator=True)
      elif self.value() == "Realm":
        queryset = queryset.filter(isRealmAdministrator=True)
    return queryset

class SetPasswordWidget (django.forms.widgets.TextInput):
  def render (self, name, value, attrs=None):
    return super(SetPasswordWidget, self).render(name, "", attrs=attrs)

class StoreUserForm (django.forms.ModelForm):
  def clean (self):
    cd = super(StoreUserForm, self).clean()
    if cd["inheritGroupShoulders"]:
      if self.instance.pk != None:
        cd["shoulders"] = self.instance.group.shoulders.all()
      else:
        if "group" in cd: cd["shoulders"] = cd["group"].shoulders.all()
    else:
      if self.instance.pk != None:
        groupShoulders = self.instance.group.shoulders.all()
      else:
        if "group" in cd:
          groupShoulders = cd["group"].shoulders.all()
        else:
          groupShoulders = []
      if any(s not in groupShoulders for s in cd["shoulders"]):
        # Should never happen.
        raise django.core.validators.ValidationError({ "shoulders":
          "User's shoulder set is not a subset of group's." })
    if cd["crossrefEnabled"]:
      if (self.instance.pk != None and\
        not self.instance.group.crossrefEnabled) or\
        (self.instance.pk == None and "group" in cd and\
        not cd["group"].crossrefEnabled):
        raise django.core.validators.ValidationError({ "crossrefEnabled":
          "Group is not Crossref enabled." })
    # Group administrators may have proxies, but not more privileged
    # users.
    if (cd["isRealmAdministrator"] or cd["isSuperuser"])\
      and len(cd["proxies"]) > 0:
      raise django.core.validators.ValidationError({ "proxies":
        "Privileged users may not have proxies." })
    if self.instance in cd["proxies"]:
      # Should never happen.
      raise django.core.validators.ValidationError({ "proxies":
        "User cannot be a proxy for itself." })
    # In a slight abuse of Django's forms logic, if the user didn't
    # enter a new password we delete the password field from the
    # cleaned data, thereby preventing it from being set in the model.
    if cd["password"].strip() != "":
      cd["password"] = cd["password"].strip()
    else:
      del cd["password"]
    return cd

def createOrUpdateUserPid (request, obj, change):
  import ezid
  import log
  f = ezid.setMetadata if change else ezid.createIdentifier
  r = f(obj.pid, models.getAdminUser(),
    { "_ezid_role": "user", "_export": "no", "_profile": "ezid",
    "ezid.user.username": obj.username,
    "ezid.user.group": "%s|%s " % (obj.group.groupname, obj.group.pid),
    "ezid.user.realm": obj.realm.name,
    "ezid.user.displayName": obj.displayName,
    "ezid.user.accountEmail": obj.accountEmail,
    "ezid.user.primaryContactName": obj.primaryContactName,
    "ezid.user.primaryContactEmail": obj.primaryContactEmail,
    "ezid.user.primaryContactPhone": obj.primaryContactPhone,
    "ezid.user.secondaryContactName": obj.secondaryContactName,
    "ezid.user.secondaryContactEmail": obj.secondaryContactEmail,
    "ezid.user.secondaryContactPhone": obj.secondaryContactPhone,
    "ezid.user.inheritGroupShoulders": str(obj.inheritGroupShoulders),
    "ezid.user.shoulders": " ".join(s.prefix for s in obj.shoulders.all()),
    "ezid.user.crossrefEnabled": str(obj.crossrefEnabled),
    "ezid.user.crossrefEmail": obj.crossrefEmail,
    "ezid.user.proxies": " ".join("%s|%s" % (u.username, u.pid)\
      for u in obj.proxies.all()),
    "ezid.user.isGroupAdministrator": str(obj.isGroupAdministrator),
    "ezid.user.isRealmAdministrator": str(obj.isRealmAdministrator),
    "ezid.user.isSuperuser": str(obj.isSuperuser),
    "ezid.user.loginEnabled": str(obj.loginEnabled),
    "ezid.user.password": obj.password,
    "ezid.user.notes": obj.notes })
  if r.startswith("success:"):
    if request != None:
      django.contrib.messages.success(request, "User PID %s." %\
        ("updated" if change else "created"))
  else:
    log.otherError("admin.createOrUpdateUserPid", Exception(
      "ezid.%s call failed: %s" % ("setMetadata" if change else\
      "createIdentifier", r)))
    if request != None:
      django.contrib.messages.error(request, "Error %s user PID." %\
        ("updating" if change else "creating"))

class StoreUserAdmin (django.contrib.admin.ModelAdmin):
  def groupLink (self, obj):
    link = django.core.urlresolvers.reverse("admin:ezidapp_storegroup_change",
      args=[obj.group.id])
    return "<a href=\"%s\">%s</a>" % (link, obj.group.groupname)
  groupLink.allow_tags = True
  groupLink.short_description = "group"
  def groupGroupname (self, obj):
    return obj.group.groupname
  groupGroupname.short_description = "group"
  def shoulderLinks (self, obj):
    return "<br/>".join("<a href=\"%s\">%s (%s)</a>" % (
      django.core.urlresolvers.reverse("admin:ezidapp_shoulder_change",
      args=[s.id]), django.utils.html.escape(s.name), s.prefix)\
      for s in obj.shoulders.all().order_by("name", "type"))
  shoulderLinks.allow_tags = True
  shoulderLinks.short_description = "links to shoulders"
  def proxyLinks (self, obj):
    return "<br/>".join("<a href=\"%s\">%s (%s)</a>" % (
      django.core.urlresolvers.reverse("admin:ezidapp_storeuser_change",
      args=[u.id]), u.username, django.utils.html.escape(u.displayName))\
      for u in obj.proxies.all().order_by("username"))
  proxyLinks.allow_tags = True
  proxyLinks.short_description = "links to proxies"
  def reverseProxyLinks (self, obj):
    return "<br/>".join("<a href=\"%s\">%s (%s)</a>" % (
      django.core.urlresolvers.reverse("admin:ezidapp_storeuser_change",
      args=[u.id]), u.username, django.utils.html.escape(u.displayName))\
      for u in obj.proxy_for.all().order_by("username"))
  reverseProxyLinks.allow_tags = True
  reverseProxyLinks.short_description = "users this user is a proxy for"
  search_fields = ["username", "displayName", "primaryContactName",
    "secondaryContactName", "notes"]
  actions = None
  list_filter = [("realm__name", StoreUserRealmFilter),
    "crossrefEnabled", StoreUserHasProxiesFilter, StoreUserIsProxyFilter,
    "loginEnabled", StoreUserAdministratorFilter]
  ordering = ["username"]
  list_display = ["username", "displayName", "groupGroupname", "realm"]
  _fieldsets = [
    (None, { "fields": ["pid", "username", None, "realm",
      "displayName", "accountEmail"] }),
    ("Primary contact", { "fields": ["primaryContactName",
      "primaryContactEmail", "primaryContactPhone"] }),
    ("Secondary contact", { "fields": ["secondaryContactName",
      "secondaryContactEmail", "secondaryContactPhone"] }),
    (None, { "fields": ["inheritGroupShoulders", "shoulders", "shoulderLinks",
      "crossrefEnabled", "crossrefEmail"] }),
    ("Proxy users", { "fields": ["proxies", "proxyLinks",
      "reverseProxyLinks"], "classes": ["collapse"] }),
    ("Authentication", { "fields": ["loginEnabled", "password",
      "isGroupAdministrator"] }),
    ("Authentication - advanced", { "fields": ["isRealmAdministrator",
      "isSuperuser"], "classes": ["collapse"] }),
    (None, { "fields": ["notes"] })]
  def get_fieldsets (self, request, obj=None):
    fs = copy.deepcopy(self._fieldsets)
    if obj != None:
      fs[0][1]["fields"][2] = "groupLink"
    else:
      fs[0][1]["fields"][2] = "group"
    return fs
  readonly_fields = ["pid", "realm", "shoulderLinks", "proxyLinks",
    "reverseProxyLinks", "groupGroupname"]
  def get_readonly_fields (self, request, obj=None):
    if obj:
      return self.readonly_fields + ["group", "groupLink"]
    else:
      return self.readonly_fields
  filter_vertical = ["proxies"]
  form = StoreUserForm
  def get_form (self, request, obj=None, **kwargs):
    form = super(StoreUserAdmin, self).get_form(request, obj, **kwargs)
    if obj != None:
      form.base_fields["shoulders"].queryset =\
        obj.group.shoulders.all().order_by("name", "type")
    else:
      form.base_fields["shoulders"].queryset = models.Shoulder.objects.none()
    form.base_fields["shoulders"].widget =\
      django.forms.CheckboxSelectMultiple()
    form.base_fields["shoulders"].help_text = None
    if obj != None:
      form.base_fields["proxies"].queryset =\
        form.base_fields["proxies"].queryset.exclude(pk=obj.pk)
    form.base_fields["password"].widget = SetPasswordWidget()
    return form
  def save_model (self, request, obj, form, change):
    if "password" in form.cleaned_data:
      obj.setPassword(form.cleaned_data["password"])
    clearCaches = False
    if change:
      obj.save()
      models.SearchUser.objects.filter(pid=obj.pid).\
        update(username=obj.username)
      clearCaches = True
    else:
      su = models.SearchUser(pid=obj.pid, username=obj.username,
        group=models.SearchGroup.objects.get(pid=obj.group.pid),
        realm=models.SearchRealm.objects.get(name=obj.realm.name))
      su.full_clean()
      obj.save()
      su.save()
    # See discussion in StoreGroupAdmin above.
    if clearCaches:
      django.db.connection.on_commit(models.store_user.clearCaches)
      django.db.connection.on_commit(models.search_identifier.clearUserCache)
    onCommitWithSqliteHack(
      lambda: createOrUpdateUserPid(request, obj, change))
  def delete_model (self, request, obj):
    obj.delete()
    models.SearchUser.objects.filter(pid=obj.pid).delete()
    django.contrib.messages.warning(request,
      "Now-defunct user PID %s not deleted; you may consider doing so." %\
      obj.pid)
    django.db.connection.on_commit(models.store_user.clearCaches)
    django.db.connection.on_commit(models.search_identifier.clearUserCache)
  class Media:
    css = { "all": ["admin/css/base-user.css"] }

superuser.register(models.StoreUser, StoreUserAdmin)

def scheduleUserChangePostCommitActions (user):
  # This function should be called when a StoreUser object is updated
  # and saved outside this module; it should be called within the
  # transaction making the updates.
  django.db.connection.on_commit(models.store_user.clearCaches)
  django.db.connection.on_commit(models.search_identifier.clearUserCache)
  onCommitWithSqliteHack(lambda: createOrUpdateUserPid(None, user, True))
