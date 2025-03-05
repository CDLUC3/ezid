#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Django admin configuration/customization

Beware: there's some
seriously occult stuff in here, and there are dependencies on the
specific version of Django used in development (1.8.1). Intimately
related to this file are the PROJECT_ROOT/templates/admin and
PROJECT_ROOT/static/admin directories.
"""


import copy
import logging

import django
import django.apps
import django.conf
import django.contrib.admin
import django.contrib.admin.sites
import django.contrib.admin.widgets
import django.contrib.messages
import django.core
import django.core.mail
import django.core.validators
import django.db
import django.db.models
import django.forms
import django.forms.widgets
import django.urls
import django.urls.resolvers
import django.utils.html

import ezidapp.models.util
import impl.ezid
import impl.log
import impl.util
from ezidapp.models.datacenter import Datacenter
from ezidapp.models.group import Group
from ezidapp.models.new_account_worksheet import NewAccountWorksheet
from ezidapp.models.realm import Realm
from ezidapp.models.shoulder import Shoulder
from ezidapp.models.user import User

logger = logging.getLogger(__name__)


class SuperuserSite(django.contrib.admin.sites.AdminSite):
    # This administrative site allows full access.
    site_header = "EZID superuser administration"
    site_title = "EZID superuser administration"
    index_title = "Administration home"

    def each_context(self, request):
        context = super(SuperuserSite, self).each_context(request)
        context["readonly_models"] = ["Shoulder", "Datacenter"]
        return context


superuser = SuperuserSite()


class ShoulderForm(django.forms.ModelForm):
    def clean(self):
        raise django.core.validators.ValidationError(
            "Object cannot be updated using this interface."
        )


class ShoulderTypeFilter(django.contrib.admin.SimpleListFilter):
    title = "type"
    parameter_name = "type"

    def lookups(self, request, model_admin):
        return [(t, t) for t in ["ARK", "DOI", "UUID"]]

    def queryset(self, request, queryset):
        if self.value() is not None:
            queryset = queryset.filter(prefix__startswith=self.value().lower() + ":")
        return queryset


class ShoulderHasMinterFilter(django.contrib.admin.SimpleListFilter):
    title = "has minter"
    parameter_name = "hasMinter"

    def lookups(self, request, model_admin):
        return [("Yes", "Yes"), ("No", "No")]

    def queryset(self, request, queryset):
        if self.value() is not None:
            if self.value() == "Yes":
                queryset = queryset.filter(~django.db.models.Q(minter=""))
            else:
                queryset = queryset.filter(minter="")
        return queryset


class ShoulderRegistrationAgencyFilter(django.contrib.admin.SimpleListFilter):
    title = "DOI registration agency"
    parameter_name = "registrationAgency"

    def lookups(self, request, model_admin):
        return [("datacite", "DataCite"), ("crossref", "Crossref")]

    def queryset(self, request, queryset):
        if self.value() is not None:
            queryset = queryset.filter(
                prefix__startswith="doi:", crossrefEnabled=(self.value() == "crossref")
            )
        return queryset


class ShoulderUnusedFilter(django.contrib.admin.SimpleListFilter):
    title = "is unused"
    parameter_name = "isUnused"

    def lookups(self, request, model_admin):
        return [("Yes", "Yes"), ("No", "No")]

    def queryset(self, request, queryset):
        if self.value() is not None:
            if self.value() == "Yes":
                queryset = queryset.filter(group__isnull=True)
            else:
                queryset = queryset.filter(group__isnull=False).distinct()
        return queryset


class GroupInline(django.contrib.admin.TabularInline):
    group_model = django.apps.apps.get_model('ezidapp', 'Group')
    model = group_model.shoulders.through
    verbose_name_plural = "Groups using this shoulder"

    def groupLink(self, obj):
        link = django.urls.reverse("admin:ezidapp_group_change", args=[obj.group.id])
        return django.utils.html.format_html('<a href="{}">{}</a>', link, obj.group.groupname)

    groupLink.allow_tags = True
    groupLink.short_description = "groupname"

    def organizationName(self, obj):
        return obj.group.organizationName

    organizationName.short_description = "organization name"

    def realm(self, obj):
        return obj.group.realm.name

    fields = ["groupLink", "organizationName", "realm"]
    readonly_fields = ["groupLink", "organizationName", "realm"]
    ordering = ["group__groupname"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UserInlineForShoulder(django.contrib.admin.TabularInline):
    user_model = django.apps.apps.get_model('ezidapp', 'User')
    model = user_model.shoulders.through
    verbose_name_plural = "Users using this shoulder"

    def userLink(self, obj):
        link = django.urls.reverse("admin:ezidapp_user_change", args=[obj.user.id])
        return django.utils.html.format_html('<a href="{}">{}</a>', link, obj.user.username)

    userLink.allow_tags = True
    userLink.short_description = "username"

    def displayName(self, obj):
        return obj.user.displayName

    displayName.short_description = "display name"

    def group(self, obj):
        return obj.user.group.groupname

    fields = ["userLink", "displayName", "group"]
    readonly_fields = ["userLink", "displayName", "group"]
    ordering = ["user__username"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ShoulderAdmin(django.contrib.admin.ModelAdmin):
    def registrationAgency(self, obj):
        if obj.isDoi:
            if obj.isDatacite:
                return "DataCite"
            elif obj.isCrossref:
                return "Crossref"
            else:
                return "?"
        else:
            return "(None)"

    registrationAgency.allow_tags = True
    registrationAgency.short_description = "DOI registration agency"

    def datacenterLink(self, obj):
        link = django.urls.reverse("admin:ezidapp_datacenter_change", args=[obj.datacenter.id])
        return django.utils.html.format_html('<a href="{}">{}</a>', link, obj.datacenter.symbol)

    datacenterLink.allow_tags = True
    datacenterLink.short_description = "datacenter"
    search_fields = ["prefix", "name"]
    actions = None
    list_filter = [
        ShoulderTypeFilter,
        ShoulderHasMinterFilter,
        ShoulderRegistrationAgencyFilter,
        ShoulderUnusedFilter,
    ]
    ordering = ["name"]
    list_display = ["prefix", "name"]
    fields = ["prefix", "name", "minter", "registrationAgency", "datacenterLink"]
    readonly_fields = [
        "prefix",
        "name",
        "minter",
        "registrationAgency",
        "datacenterLink",
    ]
    inlines = [GroupInline, UserInlineForShoulder]
    form = ShoulderForm

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


superuser.register(Shoulder, ShoulderAdmin)


class ShoulderInline(django.contrib.admin.TabularInline):
    model = Shoulder
    verbose_name_plural = "Shoulders using this datacenter"

    def shoulderLink(self, obj):
        link = django.urls.reverse("admin:ezidapp_shoulder_change", args=[obj.id])
        return django.utils.html.format_html('<a href="{}">{}</a>', link, obj.prefix)

    shoulderLink.allow_tags = True
    shoulderLink.short_description = "prefix"
    fields = ["shoulderLink", "name"]
    readonly_fields = ["shoulderLink", "name"]
    ordering = ["name"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DatacenterForm(django.forms.ModelForm):
    def clean(self):
        raise django.core.validators.ValidationError(
            "Object cannot be updated using this interface."
        )


class DatacenterAllocatorFilter(django.contrib.admin.SimpleListFilter):
    title = "allocator"
    parameter_name = "allocator"

    def lookups(self, request, model_admin):
        allocators = set()
        for dc in Datacenter.objects.all():
            allocators.add(dc.allocator)
        return [(a, a) for a in sorted(list(allocators))]

    def queryset(self, request, queryset):
        if self.value() is not None:
            queryset = queryset.filter(symbol__startswith=self.value() + ".")
        return queryset


class DatacenterUnusedFilter(django.contrib.admin.SimpleListFilter):
    title = "is unused"
    parameter_name = "isUnused"

    def lookups(self, request, model_admin):
        return [("Yes", "Yes"), ("No", "No")]

    def queryset(self, request, queryset):
        if self.value() is not None:
            if self.value() == "Yes":
                queryset = queryset.filter(shoulder__isnull=True)
            else:
                queryset = queryset.filter(shoulder__isnull=False).distinct()
        return queryset


class DatacenterAdmin(django.contrib.admin.ModelAdmin):
    search_fields = ["symbol", "name"]
    actions = None
    list_filter = [DatacenterAllocatorFilter, DatacenterUnusedFilter]
    ordering = ["symbol"]
    list_display = ["symbol", "name"]
    readonly_fields = ["symbol", "name"]
    inlines = [ShoulderInline]
    form = DatacenterForm

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


superuser.register(Datacenter, DatacenterAdmin)


class NewAccountWorksheetForm(django.forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(NewAccountWorksheetForm, self).__init__(*args, **kwargs)
        self.fields["orgStreetAddress"].widget = django.contrib.admin.widgets.AdminTextareaWidget()


class NewAccountWorksheetAdmin(django.contrib.admin.ModelAdmin):
    def organizationName(self, obj):
        if obj.orgAcronym != "":
            return f"{obj.orgName} ({obj.orgAcronym})"
        else:
            return obj.orgName

    organizationName.short_description = "organization name"
    search_fields = [
        "orgName",
        "orgAcronym",
        "orgStreetAddress",
        "reqName",
        "priName",
        "secName",
        "reqComments",
        "setGroupname",
        "setUsername",
        "setUserDisplayName",
        "setShoulderDisplayName",
        "setNotes",
    ]
    actions = None
    list_filter = ["staReady", "staShouldersCreated", "staAccountCreated"]
    ordering = ["-requestDate", "orgName"]
    list_display = ["organizationName", "requestDate"]
    fieldsets = [
        (None, {"fields": ["requestDate"]}),
        (
            "Organization",
            {"fields": ["orgName", "orgAcronym", "orgUrl", "orgStreetAddress"]},
        ),
        ("Requestor", {"fields": ["reqName", "reqEmail", "reqPhone"]}),
        (
            "Primary contact (defaults to requestor)",
            {"fields": ["priName", "priEmail", "priPhone"]},
        ),
        (
            "Secondary contact (optional)",
            {"fields": ["secName", "secEmail", "secPhone"]},
        ),
        (None, {"fields": ["accountEmail"]}),
        (
            "Request",
            {
                "fields": [
                    ("reqArks", "reqDois"),
                    "reqCrossref",
                    "reqCrossrefEmail",
                    "reqComments",
                ]
            },
        ),
        (
            "Setup",
            {
                "fields": [
                    "setRealm",
                    "setGroupname",
                    "setUsername",
                    "setUserDisplayName",
                    "setShoulderDisplayName",
                    "setNonDefaultSetup",
                    "setNotes",
                ]
            },
        ),
        (
            "Status",
            {"fields": ["staReady", "staShouldersCreated", "staAccountCreated"]},
        ),
    ]
    form = NewAccountWorksheetForm

    def save_model(self, request, obj, form, change):
        obj.save()
        newStatus = []
        for f in ["staReady", "staShouldersCreated", "staAccountCreated"]:
            if f in form.changed_data and getattr(obj, f):
                # noinspection PyProtectedMember
                newStatus.append(obj._meta.get_field(f).verbose_name)
        if len(newStatus) > 0:

            addresses = [
                a for a in django.conf.settings.EMAIL_NEW_ACCOUNT_EMAIL.split(",") if len(a) > 0
            ]
            if len(addresses) > 0:
                subject = f'New account "{str(obj)}": {", ".join(newStatus)}'
                message = (
                    "The status of a new account request has changed.\n\n"
                    "Organization: {}{}\n"
                    "Request date: {}\n"
                    "New status: {}\n\n"
                    "View the account's worksheet at:\n\n"
                    "{}{}\n\n"
                    "This is an automated email. Please do not reply.\n\n"
                    "::\n"
                    "organization_name: {}\n"
                    "organization_acronym: {}\n"
                    "organization_url: {}\n"
                    "organization_street_address: {}\n"
                    "requestor_name: {}\n"
                    "requestor_email: {}\n"
                    "requestor_phone: {}\n"
                    "primary_contact_name: {}\n"
                    "primary_contact_email: {}\n"
                    "primary_contact_phone: {}\n"
                    "secondary_contact_name: {}\n"
                    "secondary_contact_email: {}\n"
                    "secondary_contact_phone: {}\n"
                    "account_email: {}\n"
                    "arks: {}\n"
                    "dois: {}\n"
                    "crossref: {}\n"
                    "crossref_email: {}\n"
                    "requestor_comments: {}\n"
                    "realm: {}\n"
                    "groupname: {}\n"
                    "username: {}\n"
                    "user_display_name: {}\n"
                    "shoulder_display_name: {}\n"
                    "non_default_setup: {}\n"
                    "setup_notes: {}\n"
                ).format(
                    obj.orgName,
                    f" ({obj.orgAcronym})" if obj.orgAcronym != "" else "",
                    str(obj.requestDate),
                    ", ".join(newStatus),
                    django.conf.settings.EZID_BASE_URL,
                    django.urls.reverse("admin:ezidapp_newaccountworksheet_change", args=[obj.id]),
                    obj.orgName,
                    obj.orgAcronym,
                    obj.orgUrl,
                    impl.util.oneLine(obj.orgStreetAddress),
                    obj.reqName,
                    obj.reqEmail,
                    obj.reqPhone,
                    obj.priName,
                    obj.priEmail,
                    obj.priPhone,
                    obj.secName,
                    obj.secEmail,
                    obj.secPhone,
                    obj.accountEmail,
                    str(obj.reqArks),
                    str(obj.reqDois),
                    str(obj.reqCrossref),
                    obj.reqCrossrefEmail,
                    impl.util.oneLine(obj.reqComments),
                    obj.setRealm,
                    obj.setGroupname,
                    obj.setUsername,
                    obj.setUserDisplayName,
                    obj.setShoulderDisplayName,
                    str(obj.setNonDefaultSetup),
                    impl.util.oneLine(obj.setNotes),
                )
                try:
                    django.core.mail.send_mail(
                        subject, message, django.conf.settings.SERVER_EMAIL, addresses
                    )
                except Exception as e:
                    if django.conf.settings.DEBUG:
                        logging.error('#' * 100)

                    django.contrib.messages.error(
                        request, "Error sending status change email: " + str(e)
                    )
                else:
                    django.contrib.messages.success(request, "Status change email sent.")


superuser.register(NewAccountWorksheet, NewAccountWorksheetAdmin)


class RealmAdmin(django.contrib.admin.ModelAdmin):
    actions = None
    ordering = ["name"]

    def save_model(self, request, obj, form, change):
        if change:
            # Old code logic for searchRealm
            #oldName = Realm.objects.get(pk=obj.pk).name
            obj.save()
            #Realm.objects.filter(name=oldName).update(name=obj.name)
        else:
            #sr = Realm(name=obj.name)
            #sr.full_clean()
            obj.save()
            #sr.save()

    def delete_model(self, request, obj):
        obj.delete()
        #Realm.objects.filter(name=obj.name).delete()


superuser.register(Realm, RealmAdmin)


class GroupRealmFilter(django.contrib.admin.RelatedFieldListFilter):
    def __new__(cls, *args, **kwargs):
        i = django.contrib.admin.RelatedFieldListFilter.create(*args, **kwargs)
        i.title = "realm"
        return i


class GroupShoulderlessFilter(django.contrib.admin.SimpleListFilter):
    title = "shoulderless"
    parameter_name = "shoulderless"

    def lookups(self, request, model_admin):
        return [("Yes", "Yes"), ("No", "No")]

    def queryset(self, request, queryset):
        if self.value() is not None:
            if self.value() == "Yes":
                queryset = queryset.filter(shoulders=None)
            else:
                queryset = queryset.filter(~django.db.models.Q(shoulders=None))
        return queryset


class UserInlineForGroup(django.contrib.admin.TabularInline):
    model = User
    verbose_name_plural = "Users in this group"

    def userLink(self, obj):
        logger.debug("get userLink for %s", obj)
        link = django.urls.reverse("admin:ezidapp_user_change", args=[obj.id])
        return django.utils.html.format_html('<a href="{}">{}</a>', link, obj.username)

    userLink.allow_tags = True
    userLink.short_description = "username"
    fields = ["userLink", "displayName", "isGroupAdministrator"]
    readonly_fields = ["userLink", "displayName", "isGroupAdministrator"]
    ordering = ["username"]
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class GroupForm(django.forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)
        self.fields[
            "organizationStreetAddress"
        ].widget = django.contrib.admin.widgets.AdminTextareaWidget()
        self.fields["shoulders"].queryset = Shoulder.objects.filter(isTest=False).order_by(
            "name", "type"
        )


def createOrUpdateGroupPid(request, obj, change):
    f = impl.ezid.setMetadata if change else impl.ezid.createIdentifier
    logger.debug('createOrUpdateGroupPid, f= %s', f)
    r = f(
        obj.pid,
        ezidapp.models.util.getAdminUser(),
        {
            "_ezid_role": "group",
            "_export": "no",
            "_profile": "ezid",
            "ezid.group.groupname": obj.groupname,
            "ezid.group.realm": obj.realm.name,
            "ezid.group.organizationName": obj.organizationName,
            "ezid.group.organizationAcronym": obj.organizationAcronym,
            "ezid.group.organizationUrl": obj.organizationUrl,
            "ezid.group.organizationStreetAddress": obj.organizationStreetAddress,
            "ezid.group.agreementOnFile": str(obj.agreementOnFile),
            "ezid.group.crossrefEnabled": str(obj.crossrefEnabled),
            "ezid.group.shoulders": " ".join(s.prefix for s in obj.shoulders.all()),
            "ezid.group.notes": obj.notes,
        },
    )
    logger.debug('createOrUpdateGroupPid, r= %s', r)
    if r.startswith("success:"):
        django.contrib.messages.success(request, f"Group PID {'updated' if change else 'created'}.")
    else:
        impl.log.otherError(
            "admin.createOrUpdateGroupPid",
            Exception(f"ezid.{'setMetadata' if change else 'createIdentifier'} call failed: {r}"),
        )
        django.contrib.messages.error(
            request, f"Error {'updating' if change else 'creating'} group PID."
        )


def updateUserPids(request, users):
    errors = False
    for u in users:
        r = impl.ezid.setMetadata(
            u.pid,
            ezidapp.models.util.getAdminUser(),
            {
                "ezid.user.shoulders": " ".join(s.prefix for s in u.shoulders.all()),
                "ezid.user.crossrefEnabled": str(u.crossrefEnabled),
                "ezid.user.crossrefEmail": u.crossrefEmail,
            },
        )
        if not r.startswith("success:"):
            errors = True
            impl.log.otherError(
                "admin.updateUserPids", Exception("ezid.setMetadata call failed: " + r)
            )
    if errors:
        django.contrib.messages.error(request, "Error updating user PIDs.")
    else:
        django.contrib.messages.success(request, "User PIDs updated.")


class GroupAdmin(django.contrib.admin.ModelAdmin):
    def organizationNameSpelledOut(self, obj):
        return obj.organizationName

    organizationNameSpelledOut.short_description = "organization name"

    def shoulderLinks(self, obj):
        return django.utils.html.mark_safe(
            "<br/>".join(
                django.utils.html.format_html(
                    '<a href="{}">{} ({})</a>',
                    django.urls.reverse("admin:ezidapp_shoulder_change", args=[s.id]),
                    s.name,
                    s.prefix,
                )
                for s in obj.shoulders.all().order_by("name", "type")
            )
        )

    shoulderLinks.allow_tags = True
    shoulderLinks.short_description = "links to shoulders"
    search_fields = [
        "groupname",
        "organizationName",
        "organizationAcronym",
        "organizationStreetAddress",
        "notes",
    ]
    actions = None
    list_filter = [
        ("realm__name", GroupRealmFilter),
        "accountType",
        GroupShoulderlessFilter,
    ]
    ordering = ["groupname"]
    list_display = ["groupname", "organizationNameSpelledOut", "realm"]
    fieldsets = [
        (None, {"fields": ["pid", "groupname", "realm"]}),
        (
            "Organization",
            {
                "fields": [
                    "organizationName",
                    "organizationAcronym",
                    "organizationUrl",
                    "organizationStreetAddress",
                ]
            },
        ),
        (
            None,
            {
                "fields": [
                    "accountType",
                    "agreementOnFile",
                    "shoulders",
                    "shoulderLinks",
                    "notes",
                ]
            },
        ),
    ]
    readonly_fields = ["pid", "shoulderLinks"]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ["realm"]
        else:
            return self.readonly_fields

    filter_vertical = ["shoulders"]
    inlines = [UserInlineForGroup]
    form = GroupForm

    def save_model(self, request, obj, form, change):
        # obj is an instance of Group
        logger.debug("save_model, obj(%s) = %s", type(obj).__name__, obj)
        # if change:
        obj.save()
        #     # In the python3 version, this was used to create an
        #     # instance of SearchGroup to mirror obj (which is a Group)
        #     # Group.objects.filter(pid=obj.pid).update(groupname=obj.groupname)
        # else:
        #     # See above note on sg
        #     # sg = Group(
        #     #    pid=obj.pid,
        #     #    groupname=obj.groupname,
        #     #    realm=Realm.objects.get(name=obj.realm.name),
        #     # )
        #     # sg.full_clean()
        #     obj.save()
        #     # sg.save()
        # Our actions won't take effect until the Django admin's
        # transaction commits sometime in the future, so we defer clearing
        # the relevant caches. While not obvious, the following calls
        # rely on the django-transaction-hooks 3rd party package. (Django
        # 1.9 incorporates this functionality directly.)
        createOrUpdateGroupPid(request, obj, change)
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
                    for u in obj.users.all():
                        u.shoulders.remove(s)
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
                users = list(obj.users.all())
                updateUserPids(request, users)


    def delete_model(self, request, obj):
        obj.delete()
        # old logic for search group
        #Group.objects.filter(pid=obj.pid).delete()
        django.contrib.messages.warning(
            request,
            f"Now-defunct group PID {obj.pid} not deleted; you may consider doing so.",
        )

    class Media:
        css = {"all": ["admin/css/base-group.css"]}


superuser.register(Group, GroupAdmin)


class UserRealmFilter(django.contrib.admin.RelatedFieldListFilter):
    def __new__(cls, *args, **kwargs):
        i = django.contrib.admin.RelatedFieldListFilter.create(*args, **kwargs)
        i.title = "realm"
        return i


class UserHasProxiesFilter(django.contrib.admin.SimpleListFilter):
    title = "has proxies"
    parameter_name = "hasProxies"

    def lookups(self, request, model_admin):
        return [("Yes", "Yes"), ("No", "No")]

    def queryset(self, request, queryset):
        if self.value() is not None:
            if self.value() == "Yes":
                queryset = queryset.filter(~django.db.models.Q(proxies=None))
            else:
                queryset = queryset.filter(proxies=None)
        return queryset


class UserIsProxyFilter(django.contrib.admin.SimpleListFilter):
    title = "is proxy"
    parameter_name = "isProxy"

    def lookups(self, request, model_admin):
        return [("Yes", "Yes"), ("No", "No")]

    def queryset(self, request, queryset):
        if self.value() is not None:
            if self.value() == "Yes":
                queryset = queryset.filter(user__isnull=False).distinct()
            else:
                queryset = queryset.filter(user__isnull=True)
        return queryset


class UserAdministratorFilter(django.contrib.admin.SimpleListFilter):
    title = "is administrator"
    parameter_name = "administrator"

    def lookups(self, request, model_admin):
        return [("No", "No"), ("Group", "Group"), ("Realm", "Realm")]

    def queryset(self, request, queryset):
        if self.value() is not None:
            if self.value() == "No":
                queryset = (
                    queryset.filter(isGroupAdministrator=False)
                    .filter(isRealmAdministrator=False)
                    .filter(isSuperuser=False)
                )
            elif self.value() == "Group":
                queryset = queryset.filter(isGroupAdministrator=True)
            elif self.value() == "Realm":
                queryset = queryset.filter(isRealmAdministrator=True)
        return queryset


class SetPasswordWidget(django.forms.widgets.TextInput):
    # noinspection PyMethodOverriding
    # def render(self, name, value, attrs=None):
    def render(self, name, value, attrs=None, renderer=None):
        return super(SetPasswordWidget, self).render(name, "", attrs=attrs)


class UserForm(django.forms.ModelForm):
    def clean(self):
        cd = super(UserForm, self).clean()
        if cd["inheritGroupShoulders"]:
            if self.instance.pk is not None:
                cd["shoulders"] = self.instance.group.shoulders.all()
            else:
                if "group" in cd:
                    cd["shoulders"] = cd["group"].shoulders.all()
        else:
            if self.instance.pk is not None:
                groupShoulders = self.instance.group.shoulders.all()
            else:
                if "group" in cd:
                    groupShoulders = cd["group"].shoulders.all()
                else:
                    groupShoulders = []
            if any(s not in groupShoulders for s in cd["shoulders"]):
                # Should never happen.
                raise django.core.validators.ValidationError(
                    {"shoulders": "User's shoulder set is not a subset of group's."}
                )
        if cd.get("crossrefEnabled", False):
            if (self.instance.pk is not None and not self.instance.group.crossrefEnabled) or (
                self.instance.pk is None and "group" in cd and not cd["group"].crossrefEnabled
            ):
                raise django.core.validators.ValidationError(
                    {"crossrefEnabled": "Group is not Crossref enabled."}
                )
        # Group administrators may have proxies, but not more privileged
        # users.
        if (cd["isRealmAdministrator"] or cd["isSuperuser"]) and len(cd["proxies"]) > 0:
            raise django.core.validators.ValidationError(
                {"proxies": "Privileged users may not have proxies."}
            )
        if self.instance in cd["proxies"]:
            # Should never happen.
            raise django.core.validators.ValidationError(
                {"proxies": "User cannot be a proxy for itself."}
            )
        # In a slight abuse of Django's forms logic, if the user didn't
        # enter a new password we delete the password field from the
        # cleaned data, thereby preventing it from being set in the model.
        if cd["password"].strip() != "":
            cd["password"] = cd["password"].strip()
        else:
            del cd["password"]
        return cd


def createOrUpdateUserPid(request, obj, change):
    logger.debug(f'createOrUpdateUserPid() obj={repr(obj)}, change={repr(change)}')
    f = impl.ezid.setMetadata if change else impl.ezid.createIdentifier
    r = f(
        obj.pid,
        ezidapp.models.util.getAdminUser(),
        {
            "_ezid_role": "user",
            "_export": "no",
            "_profile": "ezid",
            "ezid.user.username": obj.username,
            "ezid.user.group": f"{obj.group.groupname}|{obj.group.pid} ",
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
            "ezid.user.proxies": " ".join(f"{u.username}|{u.pid}" for u in obj.proxies.all()),
            "ezid.user.isGroupAdministrator": str(obj.isGroupAdministrator),
            "ezid.user.isRealmAdministrator": str(obj.isRealmAdministrator),
            "ezid.user.isSuperuser": str(obj.isSuperuser),
            "ezid.user.loginEnabled": str(obj.loginEnabled),
            "ezid.user.password": obj.password,
            "ezid.user.notes": obj.notes,
        },
    )
    if r.startswith("success:"):
        if request is not None:
            django.contrib.messages.success(
                request, f"User PID {'updated' if change else 'created'}."
            )
    else:
        impl.log.otherError(
            "admin.createOrUpdateUserPid",
            Exception(f"ezid.{'setMetadata' if change else 'createIdentifier'} call failed: {r}"),
        )
        if request is not None:
            django.contrib.messages.error(
                request, f"Error {'updating' if change else 'creating'} user PID."
            )


class UserAdmin(django.contrib.admin.ModelAdmin):
    def groupLink(self, obj):
        link = django.urls.reverse("admin:ezidapp_group_change", args=[obj.group.id])
        return django.utils.html.format_html('<a href="{}">{}</a>', link, obj.group.groupname)

    groupLink.allow_tags = True
    groupLink.short_description = "group"

    def groupGroupname(self, obj):
        return obj.group.groupname

    groupGroupname.short_description = "group"

    def shoulderLinks(self, obj):
        return django.utils.html.mark_safe(
            "<br/>".join(
                django.utils.html.format_html(
                    '<a href="{}">{} ({})</a>',
                    django.urls.reverse("admin:ezidapp_shoulder_change", args=[s.id]),
                    s.name,
                    s.prefix,
                )
                for s in obj.shoulders.all().order_by("name", "type")
            )
        )

    shoulderLinks.allow_tags = True
    shoulderLinks.short_description = "links to shoulders"

    def proxyLinks(self, obj):
        return django.utils.html.mark_safe(
            "<br/>".join(
                django.utils.html.format_html(
                    '<a href="{}">{} ({})</a>',
                    django.urls.reverse("admin:ezidapp_user_change", args=[u.id]),
                    u.username,
                    django.utils.html.escape(u.displayName),
                )
                for u in obj.proxies.all().order_by("username")
            )
        )

    proxyLinks.allow_tags = True
    proxyLinks.short_description = "links to proxies"

    def reverseProxyLinks(self, obj):
        return django.utils.html.mark_safe(
            "<br/>".join(
                django.utils.html.format_html(
                    '<a href="{}">{} ({})</a>',
                    django.urls.reverse("admin:ezidapp_user_change", args=[u.id]),
                    u.username,
                    django.utils.html.escape(u.displayName),
                )
                for u in obj.proxy_for.all().order_by("username")
            )
        )

    reverseProxyLinks.allow_tags = True
    reverseProxyLinks.short_description = "users this user is a proxy for"
    search_fields = [
        "username",
        "displayName",
        "primaryContactName",
        "secondaryContactName",
        "notes",
    ]
    actions = None
    list_filter = [
        ("realm__name", UserRealmFilter),
        UserHasProxiesFilter,
        UserIsProxyFilter,
        "loginEnabled",
        UserAdministratorFilter,
    ]
    ordering = ["username"]
    list_display = ["username", "displayName", "groupGroupname", "realm"]
    _fieldsets = [
        (
            None,
            {
                "fields": [
                    "pid",
                    "username",
                    None,
                    "realm",
                    "displayName",
                    "accountEmail",
                ]
            },
        ),
        (
            "Primary contact",
            {
                "fields": [
                    "primaryContactName",
                    "primaryContactEmail",
                    "primaryContactPhone",
                ]
            },
        ),
        (
            "Secondary contact",
            {
                "fields": [
                    "secondaryContactName",
                    "secondaryContactEmail",
                    "secondaryContactPhone",
                ]
            },
        ),
        (
            None,
            {
                "fields": [
                    "inheritGroupShoulders",
                    "shoulders",
                    "shoulderLinks",
                    "crossrefEmail",
                ]
            },
        ),
        (
            "Proxy users",
            {
                "fields": ["proxies", "proxyLinks", "reverseProxyLinks"],
                "classes": ["collapse"],
            },
        ),
        (
            "Authentication",
            {"fields": ["loginEnabled", "password", "isGroupAdministrator"]},
        ),
        (
            "Authentication - advanced",
            {
                "fields": ["isRealmAdministrator", "isSuperuser"],
                "classes": ["collapse"],
            },
        ),
        (None, {"fields": ["notes"]}),
    ]

    def get_fieldsets(self, request, obj=None):
        fs = copy.deepcopy(self._fieldsets)
        if obj is not None:
            fs[0][1]["fields"][2] = "groupLink"
        else:
            fs[0][1]["fields"][2] = "group"
        return fs

    readonly_fields = [
        "pid",
        "realm",
        "shoulderLinks",
        "proxyLinks",
        "reverseProxyLinks",
        "groupGroupname",
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ["group", "groupLink"]
        else:
            return self.readonly_fields

    filter_vertical = ["proxies"]
    form = UserForm

    def get_form(self, request, obj=None, **kwargs):
        form = super(UserAdmin, self).get_form(request, obj, **kwargs)
        if obj is not None:
            form.base_fields["shoulders"].queryset = obj.group.shoulders.all().order_by(
                "name", "type"
            )
        else:
            form.base_fields["shoulders"].queryset = Shoulder.objects.none()
        form.base_fields["shoulders"].widget = django.forms.CheckboxSelectMultiple()
        form.base_fields["shoulders"].help_text = None
        if obj is not None:
            form.base_fields["proxies"].queryset = form.base_fields["proxies"].queryset.exclude(
                pk=obj.pk
            )
        form.base_fields["password"].widget = SetPasswordWidget()
        return form

    def save_model(self, request, obj, form, change):
        """
        obj: User instance
        """
        logger.debug("UserAdmin.save_model: obj(%s): %s", type(obj).__name__, obj)
        if "password" in form.cleaned_data:
            obj.setPassword(form.cleaned_data["password"])
        obj.save()
        # if change:
        #     obj.save()
        #     # This was previously used to update the SearchUser info
        #     # User.objects.filter(pid=obj.pid).update(username=obj.username)
        # else:
        #     # old code - su = SearchUser instance
        #     #su = User(
        #     #    pid=obj.pid,
        #     #    username=obj.username,
        #     #    group=Group.objects.get(pid=obj.group.pid),
        #     #    realm=Realm.objects.get(name=obj.realm.name),
        #     #)
        #     #su.full_clean()
        #     obj.save()
        #     #su.save()
        # # See discussion in GroupAdmin above.
        createOrUpdateUserPid(request, obj, change)

    def delete_model(self, request, obj):
        obj.delete()
        #User.objects.filter(pid=obj.pid).delete()
        django.contrib.messages.warning(
            request,
            f"Now-defunct user PID {obj.pid} not deleted; you may consider doing so.",
        )

    class Media:
        css = {"all": ["admin/css/base-user.css"]}


superuser.register(User, UserAdmin)


def scheduleUserChangePostCommitActions(user):
    # This function should be called when a User object is updated
    # and saved outside this module; it should be called within the
    # transaction making the updates.
    createOrUpdateUserPid(None, user, True)
