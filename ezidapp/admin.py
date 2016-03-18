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

import django.contrib.admin
import django.contrib.messages
import django.core.urlresolvers
import django.core.validators
import django.forms

import config
import models
import ui_common

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
      ui_common.alertMessage = obj.alertMessage
    if obj.secretKey == "":
      config.reload()
      django.contrib.messages.success(request, "Server reloaded.")
    return obj

superuser.register(models.ServerVariables, ServerVariablesAdmin)

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
