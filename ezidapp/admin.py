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
import django.db.models
import django.forms

import models
import util

# Deferred imports...
"""
import config
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
    return obj.orgName
  organizationName.short_description = "organization name"
  search_fields = ["orgName", "orgAcronym", "orgStreetAddress", "reqName",
    "priName", "secName", "reqUsername", "reqAccountDisplayName",
    "reqShoulderName", "reqComments", "setGroupname", "setUsername",
    "setDatacenter", "setNotes"]
  actions = None
  list_filter = ["staReady", "staShouldersCreated", "staAccountCreated"]
  ordering = ["-requestDate", "orgName"]
  list_display = ["organizationName", "requestDate"]
  fieldsets = [
    (None, { "fields": ["requestDate"] }),
    ("Organization", { "fields": ["orgName", "orgAcronym", "orgUrl",
      "orgStreetAddress"] }),
    ("Requestor", { "fields": ["reqName", "reqEmail", "reqPhone"] }),
    ("Primary contact", { "fields": [("priName", "priUseRequestor"),
      "priEmail", "priPhone"] }),
    ("Secondary contact (optional)", { "fields": ["secName", "secEmail",
      "secPhone"] }),
    ("Request", { "fields": ["reqUsername", ("reqAccountDisplayName",
      "reqAccountDisplayNameUseOrganization"), ("reqAccountEmail",
      "reqAccountEmailUsePrimary"), ("reqArks", "reqDois"),
      ("reqShoulderName", "reqShoulderNameUseOrganization"), "reqShoulders",
      "reqCrossref", ("reqCrossrefEmail", "reqCrossrefEmailUseAccount"),
      "reqHasExistingIdentifiers", "reqComments"] }),
    ("Setup", { "fields": ["setRealm", ("setGroupname", "setExistingGroup"),
      ("setUsername", "setUsernameUseRequested"), "setNeedShoulders",
      "setNeedMinters", ("setDatacenter", "setExistingDatacenter"),
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
        subject = "New account \"%s, %s\": %s" % (obj.orgName,
          str(obj.requestDate), ", ".join(newStatus))
        message = ("The status of a new account request has changed.\n\n" +\
          "Organization: %s\n" +\
          "Request date: %s\n" +\
          "New status: %s\n\n" +\
          "View the account's worksheet at:\n\n" +\
          "%s%s\n\n" +\
          "This is an automated email.  Please do not reply.\n\n" +\
          "::\n" +\
          "organization_name: %s\n" +\
          "organization_acronym: %s\n" +\
          "new_shoulders_required: %s\n" +\
          "arks: %s\n" +\
          "dois: %s\n" +\
          "minters_required: %s\n" +\
          "shoulder_name: %s\n" +\
          "requested_shoulder_branding: %s\n" +\
          "realm: %s\n" +\
          "datacenter: %s\n" +\
          "existing_datacenter: %s\n" +\
          "crossref: %s\n" +\
          "notes: %s\n") %\
          (obj.orgName, str(obj.requestDate), ", ".join(newStatus),
          config.get("DEFAULT.ezid_base_url"),
          django.core.urlresolvers.reverse(
          "admin:ezidapp_newaccountworksheet_change", args=[obj.id]),
          obj.orgName, obj.orgAcronym,
          str(obj.setNeedShoulders), str(obj.reqArks), str(obj.reqDois),
          str(obj.setNeedMinters), obj.reqShoulderName, obj.reqShoulders,
          obj.setRealm, obj.setDatacenter,
          str(obj.setExistingDatacenter), str(obj.reqCrossref),
          util.oneLine(obj.setNotes))
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
    models.SearchRealm.objects.filter(name=obj.name).delete()
    obj.delete()

superuser.register(models.StoreRealm, StoreRealmAdmin)
