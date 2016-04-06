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
    return [(t, t) for t in ["ARK", "DOI", "URN"]]
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
    "crossrefEnabled"]
  ordering = ["name"]
  list_display = ["prefix", "name"]
  fields = ["prefix", "name", "minter", "datacenterLink", "crossrefEnabled"]
  readonly_fields = ["prefix", "name", "minter", "datacenterLink",
    "crossrefEnabled"]
  inlines = [StoreGroupInline]
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

class StoreDatacenterAdmin (django.contrib.admin.ModelAdmin):
  search_fields = ["symbol", "name"]
  actions = None
  list_filter = [StoreDatacenterAllocatorFilter]
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

class StoreGroupForm (django.forms.ModelForm):
  def __init__ (self, *args, **kwargs):
    super(StoreGroupForm, self).__init__(*args, **kwargs)
    self.fields["organizationStreetAddress"].widget =\
      django.contrib.admin.widgets.AdminTextareaWidget()
    self.fields["shoulders"].queryset = models.Shoulder.objects.filter(
      isTest=False).order_by("name", "type")

def createOrUpdateGroupPid (request, obj, change):
  import config
  import ezid
  import log
  r = ezid.asAdmin(ezid.setMetadata if change else ezid.createIdentifier,
    obj.pid,
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
    # the relevant caches.
    if clearCaches:
      django.db.connection.on_commit(models.store_group.clearCaches)
      django.db.connection.on_commit(models.search_identifier.clearGroupCache)
    # Oy vay was this difficult.  A conflict in SQLite between the
    # Django transaction mechanism and the explicit transactions done
    # in the legacy 'store' module means that the PID update must be
    # done outside the Django transaction.  But the Django admin app
    # puts a transaction around the entire HTTP request, so our only
    # choice is to perform the update upon commit.  However, on-commit
    # hooks were added only in Django 1.9, which, as of this writing,
    # we are not yet using.  So, while not obvious, the following call
    # relies on the django-transaction-hooks 3rd party package.
    django.db.connection.on_commit(
      lambda: createOrUpdateGroupPid(request, obj, change))
    # TEMPORARY LDAP BRIDGE
    import ezidadmin
    if change:
      django.db.connection.on_commit(
        lambda: ezidadmin.groupUpdateBridge(request, obj))
    else:
      django.db.connection.on_commit(
        lambda: ezidadmin.groupCreateBridge(request, obj))
  def delete_model (self, request, obj):
    obj.delete()
    models.SearchGroup.objects.filter(pid=obj.pid).delete()
    django.contrib.messages.warning(request,
      "Now-defunct group PID %s not deleted; you may consider doing so." %\
      obj.pid)
    # See comment above.
    django.db.connection.on_commit(models.store_group.clearCaches)
    django.db.connection.on_commit(models.search_identifier.clearGroupCache)
    # TEMPORARY LDAP BRIDGE
    import ezidadmin
    django.db.connection.on_commit(
      lambda: ezidadmin.groupDeleteBridge(request, obj))

superuser.register(models.StoreGroup, StoreGroupAdmin)
