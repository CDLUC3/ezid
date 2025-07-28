#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf
import django.contrib.messages
import django.db.models
import django.http
import django.shortcuts
import django.urls.resolvers
from django.utils.translation import gettext as _

import impl.datacite
import impl.datacite_xml
import impl.download
import impl.erc
import impl.ezid
import impl.form_objects
import impl.mapping
import impl.metadata
import impl.policy
import impl.ui_common
import impl.ui_create
import impl.ui_search
import impl.userauth
import impl.util2

FORM_VALIDATION_ERROR_ON_LOAD = _("One or more fields do not validate. ") + _(
    "Please check the highlighted fields below for details."
)


# noinspection PyDictCreation
@impl.ui_common.user_login_required
def index(request):
    """Manage Page, listing all Ids owned by user, or if groupadmin, all group
    users."""
    d = {'menu_item': 'ui_manage.index'}
    d['collapse_advanced_search'] = "collapsed"
    if request.method != "GET":
        return impl.ui_common.methodNotAllowed(request)
    noConstraintsReqd = True  # Empty 'manage' form means search everything
    d['q'] = impl.ui_search.queryDict(request)
    user = impl.userauth.getUser(request)
    d['owner_selected'] = (
        _defaultUser(user)
        if not ('owner_selected' in request.GET) or request.GET['owner_selected'] == ''
        else request.GET['owner_selected']
    )
    d['form'] = impl.form_objects.ManageSearchIdForm(d['q'])
    # order_by and sort are initial sorting defaults. The request trumps these.
    d['order_by'] = 'c_update_time'
    d['sort'] = 'asc'
    d['owner_names'] = impl.ui_common.owner_names(user, "manage")
    # Check if anything has actually been entered into search fields
    searchfields = {
        k: v
        for k, v in list(d['q'].items())
        if k not in ['sort', 'ps', 'order_by', 'owner_selected']
    }
    searchfields = [_f for _f in list(searchfields.values()) if _f]
    if searchfields:
        noConstraintsReqd = False
        d[
            'filtered'
        ] = True  # Flag for template to provide option of searching on all IDs
    d = impl.ui_search.search(d, request, noConstraintsReqd, "manage")
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, 'manage/index', d)


def _defaultUser(user):
    """Pick current user."""
    # ToDo: Make sure this works for Realm Admin and picking Groups
    return (
        'all'
        if user.isSuperuser
        else "group_" + user.group.groupname
        if user.isGroupAdministrator
        else "user_" + user.username
    )


def _getLatestMetadata(identifier, request, prefixMatch=False):
    """The successful return is a pair (status, dictionary) where 'status' is a
    string that includes the canonical, qualified form of the identifier, as
    in:

    success: doi:10.5060/FOO
    and 'dictionary' contains element (name, value) pairs.
    """
    return impl.ezid.getMetadata(
        identifier, impl.userauth.getUser(request, returnAnonymous=True), prefixMatch
    )


def _updateEzid(request, d, stts, m_to_upgrade=None):
    """Take data from form fields in /manage/edit and applies them to IDs
    metadata If m_to_upgrade is specified, converts record to advanced datacite
    Returns ezid.setMetadata (successful return is the identifier string) Also
    removes tags related to old profile if converting to advanced datacite."""
    m_dict = {
        '_target': request.POST['target'],
        '_status': stts,
        '_export': ('yes' if (not 'export' in d) or d['export'] == 'yes' else 'no'),
    }
    if m_to_upgrade:
        d['current_profile'] = impl.metadata.getProfile('datacite')
        # datacite_xml ezid profile is defined by presence of 'datacite' assigned to the
        # '_profile' key and XML present in the 'datacite' key
        m_dict['datacite'] = impl.datacite.formRecord(d['id_text'], m_to_upgrade, True)
        m_dict['_profile'] = 'datacite'
        # Old tag cleanup
        if m_to_upgrade.get("_profile", "") == "datacite":
            m_dict['datacite.creator'] = ''
            m_dict['datacite.publisher'] = ''
            m_dict['datacite.publicationyear'] = ''
            m_dict['datacite.title'] = ''
            m_dict['datacite.type'] = ''
        if m_to_upgrade.get("_profile", "") == "dc":
            m_dict['dc.creator'] = ''
            m_dict['dc.date'] = ''
            m_dict['dc.publisher'] = ''
            m_dict['dc.title'] = ''
            m_dict['dc.type'] = ''
        if m_to_upgrade.get("_profile", "") == "erc":
            m_dict['erc.who'] = ''
            m_dict['erc.what'] = ''
            m_dict['erc.when'] = ''
    # ToDo: Using current_profile here, but isn't this confusing if executing simpleToAdvanced
    to_write = impl.ui_common.assembleUpdateDictionary(
        request, d['current_profile'], m_dict
    )
    return impl.ezid.setMetadata(
        d['id_text'], impl.userauth.getUser(request, returnAnonymous=True), to_write
    )


def _alertMessageUpdateError(request, s):
    django.contrib.messages.error(
        request,
        _("There was an error updating the metadata for your identifier") + ": " + s,
    )


def _alertMessageUpdateSuccess(request):
    django.contrib.messages.success(request, _("Identifier updated."))


def _assignManualTemplate(d):
    # [TODO: Enhance advanced DOI ERC profile to allow for elements ERC + datacite.publisher or
    #    ERC + dc.publisher.] For now, just hide this profile.
    # if d['id_text'].startswith("doi:"):
    #  d['profiles'][:] = [p for p in d['profiles'] if not p.name == 'erc']
    d['manual_profile'] = True
    d['manual_template'] = 'create/_datacite_xml.html'
    d['polygon_view'] = 'edit'
    return d


# noinspection PyDictCreation
def edit(request, identifier):
    """Edit page for a given ID."""
    d = {'menu_item': 'ui_manage.null'}
    d["testPrefixes"] = django.conf.settings.TEST_SHOULDER_DICT
    r = _getLatestMetadata(identifier, request)
    if type(r) is str:
        django.contrib.messages.error(request, impl.ui_common.formatError(r))
        return django.shortcuts.redirect("ui_manage.index")
    s, id_metadata = r
    if not impl.policy.authorizeUpdateLegacy(
        impl.userauth.getUser(request, returnAnonymous=True),
        id_metadata["_owner"],
        id_metadata["_ownergroup"],
    ):
        django.contrib.messages.error(
            request,
            _(
                "You are not allowed to edit this identifier. "
                + "If this ID belongs to you and you'd like to edit, please log in."
            ),
        )
        return django.shortcuts.redirect("/id/" + urllib.parse.quote(identifier, ":/"))
    d['identifier'] = id_metadata
    t_stat = [x.strip() for x in id_metadata['_status'].split("|", 1)]
    d['pub_status'] = t_stat[0]
    d['orig_status'] = t_stat[0]
    d['stat_reason'] = None
    if t_stat[0] == 'unavailable' and len(t_stat) > 1:
        d['stat_reason'] = t_stat[1]
    d['export'] = id_metadata['_export'] if '_export' in id_metadata else 'yes'
    d['id_text'] = s.split()[1]
    d['id_as_url'] = impl.util2.urlForm(d['id_text'])
    d['internal_profile'] = impl.metadata.getProfile('internal')
    d['profiles'] = impl.metadata.getProfiles()[1:]

    if request.method == "GET":
        d['is_test_id'] = _isTestId(d['id_text'], d['testPrefixes'])
        if '_profile' in id_metadata:
            d['current_profile'] = impl.metadata.getProfile(id_metadata['_profile'])
        else:
            d['current_profile'] = impl.metadata.getProfile('dc')
        if d['current_profile'].name == 'datacite' and 'datacite' in id_metadata:
            d = _assignManualTemplate(d)
            form_coll = impl.datacite_xml.dataciteXmlToFormElements(
                d['identifier']['datacite']
            )
            # This is the only item from internal profile that needs inclusion in django form framework
            form_coll.nonRepeating['target'] = id_metadata['_target']
            d['form'] = impl.form_objects.getIdForm_datacite_xml(form_coll, request)
            if not impl.form_objects.isValidDataciteXmlForm(d['form']):
                django.contrib.messages.error(request, FORM_VALIDATION_ERROR_ON_LOAD)
        else:
            if "form_placeholder" not in d:
                d['form_placeholder'] = None
            d['form'] = impl.form_objects.getIdForm(
                d['current_profile'], d['form_placeholder'], id_metadata
            )
            if not d['form'].is_valid():
                django.contrib.messages.error(request, FORM_VALIDATION_ERROR_ON_LOAD)
    elif request.method == "POST":
        post = request.POST
        d['pub_status'] = post['_status'] if '_status' in post else d['pub_status']
        d['stat_reason'] = (
            post['stat_reason'] if 'stat_reason' in post else d['stat_reason']
        )
        d['export'] = post['_export'] if '_export' in post else d['export']
        ''' Profiles could previously be switched in edit template, thus generating
        posibly two differing profiles (current vs original). So we previously did a 
        check here to confirm current_profile equals original profile before saving.'''

        # noinspection PyTypeChecker
        d['current_profile'] = impl.metadata.getProfile(
            post.get('original_profile', d['identifier']['_profile'])
        )

        if post['_status'] == 'unavailable':
            stts = post['_status'] + " | " + post['stat_reason']
        else:
            stts = post['_status']

        if d['current_profile'].name == 'datacite' and 'datacite' in id_metadata:
            d = _assignManualTemplate(d)
            d = impl.ui_create.validate_adv_form_datacite_xml(request, d)
            if 'id_gen_result' in d:
                # noinspection PyUnresolvedReferences
                return impl.ui_common.render(
                    request, 'manage/edit', d
                )  # ID Creation page
            else:
                assert 'generated_xml' in d
                to_write = {
                    "_profile": 'datacite',
                    '_target': post['target'],
                    "_status": stts,
                    "_export": d['export'],
                    "datacite": d['generated_xml'],
                }
                s = impl.ezid.setMetadata(
                    post['identifier'],
                    impl.userauth.getUser(request, returnAnonymous=True),
                    to_write,
                )
                if s.startswith("success:"):
                    _alertMessageUpdateSuccess(request)
                    return django.shortcuts.redirect(
                        "/id/" + urllib.parse.quote(identifier, ":/")
                    )
                else:
                    _alertMessageUpdateError(request, s)
        else:
            """Even if converting from simple to advanced, let's make sure
            forms validate and update identifier first, else don't upgrade."""
            d['form'] = impl.form_objects.getIdForm(d['current_profile'], None, post)
            if d['form'].is_valid():
                result = _updateEzid(request, d, stts)
                if not result.startswith("success:"):
                    d['current_profile'] = impl.metadata.getProfile(
                        id_metadata['_profile']
                    )
                    _alertMessageUpdateError(request, result)
                    # noinspection PyUnresolvedReferences
                    return impl.ui_common.render(request, "manage/edit", d)
                else:
                    if (
                        'simpleToAdvanced' in post
                        and post['simpleToAdvanced'] == 'True'
                    ):
                        # Convert simple ID to advanced (datacite with XML)
                        result = _updateEzid(request, d, stts, id_metadata)
                        r = _getLatestMetadata(identifier, request)
                        if type(r) is str:
                            django.contrib.messages.error(
                                request, impl.ui_common.formatError(r)
                            )
                            return django.shortcuts.redirect("ui_manage.index")
                        _s, _id_metadata = r
                        if not result.startswith("success:"):
                            #  if things fail, just display same simple edit page with error
                            _alertMessageUpdateError(request, result)
                        else:
                            _alertMessageUpdateSuccess(request)
                            return django.shortcuts.redirect(
                                "/id/" + urllib.parse.quote(identifier, ":/")
                            )
                    else:
                        _alertMessageUpdateSuccess(request)
                        return django.shortcuts.redirect(
                            "/id/" + urllib.parse.quote(identifier, ":/")
                        )
    else:
        return impl.ui_common.methodNotAllowed(request)
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, "manage/edit", d)


_simpleSchemaDotOrgResourceMap = {
    "Audiovisual": "MediaObject",
    "Collection": "CreativeWork",
    "Dataset": "Dataset",
    "Event": "CreativeWork",
    "Image": "ImageObject",
    "InteractiveResource": "CreativeWork",
    "Model": "CreativeWork",
    "PhysicalObject": "CreativeWork",
    "Service": "Service",
    "Software": "SoftwareSourceCode",
    "Sound": "AudioObject",
    "Text": "ScholarlyArticle",
    "Workflow": "CreativeWork",
    "Other": "CreativeWork",
}


def _getSchemaDotOrgType(km_type):
    try:
        return _simpleSchemaDotOrgResourceMap[km_type]
    except Exception:
        return "CreativeWork"


def _schemaDotOrgMetadata(km, id_as_url):
    d = {'@context': 'http://schema.org', '@id': id_as_url, 'identifier': id_as_url}
    if km.creator:
        authors = [a.strip() for a in km.creator.split(";")]
        d['author'] = authors[0] if len(authors) == 1 else authors
    if km.validatedDate:
        d['datePublished'] = km.validatedDate
    if km.publisher:
        d['publisher'] = km.publisher
    if km.title:
        d['name'] = km.title
    km_type = km.validatedType.split("/") if km.validatedType else None
    if km_type:
        d['@type'] = _getSchemaDotOrgType(km_type[0])
        if km_type[0] == "Service":  # No real match in schema.org for this type
            if 'datePublished' in d:
                del d['datePublished']
            if 'publisher' in d:
                del d['publisher']
            if 'author' in d:
                del d['author']
        elif len(km_type) > 1:
            d['learningResourceType'] = km_type[1]
    else:
        d['@type'] = "CreativeWork"
    return json.dumps(d, indent=2, sort_keys=True)


# noinspection PyDictCreation
def details(request):
    """ID Details page for a given ID."""
    d = {'menu_item': 'ui_manage.null'}
    d["testPrefixes"] = django.conf.settings.TEST_SHOULDER_DICT
    identifier = request.path_info[len("/id/") :]
    r = _getLatestMetadata(
        identifier,
        request,
        prefixMatch=(request.GET.get("prefix_match", "no").lower() == "yes"),
    )
    if type(r) is str:
        django.contrib.messages.error(
            request, impl.ui_common.formatError(r + ":&nbsp;&nbsp;" + identifier)
        )
        # ToDo: Pass details in from previous screen so we know where to send redirect back to
        if impl.userauth.getUser(request) is None:
            return django.shortcuts.redirect("ui_search.index")
        else:
            return django.shortcuts.redirect("ui_home.index")
    s, id_metadata = r
    assert s.startswith("success:")
    if " in_lieu_of " in s:
        newid = s.split()[1]
        django.contrib.messages.info(
            request, f"Identifier {newid} returned in lieu of {identifier}."
        )
        return django.shortcuts.redirect("/id/" + urllib.parse.quote(newid, ":/"))
    d['allow_update'] = impl.policy.authorizeUpdateLegacy(
        impl.userauth.getUser(request, returnAnonymous=True),
        id_metadata["_owner"],
        id_metadata["_ownergroup"],
    )
    d['identifier'] = id_metadata
    d['id_text'] = s.split()[1]
    d['id_as_url'] = impl.util2.urlForm(d['id_text'])
    d['is_test_id'] = _isTestId(d['id_text'], d['testPrefixes'])
    d['internal_profile'] = impl.metadata.getProfile('internal')
    d['target'] = id_metadata['_target']
    d['current_profile'] = impl.metadata.getProfile(
        id_metadata['_profile']
    ) or impl.metadata.getProfile('erc')
    d['recent_creation'] = identifier.startswith('doi') and (
        time.time() - float(id_metadata['_created']) < 60 * 30
    )
    d['recent_update'] = identifier.startswith('doi') and (
        time.time() - float(id_metadata['_updated']) < 60 * 30
    )
    if d['current_profile'].name == 'datacite' and 'datacite' in id_metadata:
        r = impl.datacite.dcmsRecordToHtml(id_metadata['datacite'])
        if r:
            d['datacite_html'] = r
        
        converted_rd = impl.datacite.removeXMLNamespacePrefix(id_metadata['datacite'])
        brief_record = impl.datacite.briefDataciteRecord(converted_rd)
        brief_record_keys = [
            'datacite.creator',
            'datacite.title',
            'datacite.publicationyear',
            'datacite.publisher',
            'datacite.resourcetype',
        ]
        for key in brief_record_keys:
            if key in brief_record:
                d["identifier"][key] = brief_record[key]

    if (
        d['current_profile'].name == 'crossref'
        and 'crossref' in id_metadata
        and id_metadata['crossref'].strip() != ""
    ):
        d['has_crossref_metadata'] = True
    t_stat = [x.strip() for x in id_metadata['_status'].split("|", 1)]
    d['pub_status'] = t_stat[0]
    if t_stat[0] == 'unavailable' and len(t_stat) > 1:
        d['stat_reason'] = t_stat[1]
    if t_stat[0] == 'public' and identifier.startswith("ark:/"):
        d['schemaDotOrgMetadata'] = _schemaDotOrgMetadata(
            impl.mapping.map(id_metadata), d['id_as_url']
        )
    d['has_block_data'] = impl.ui_common.identifier_has_block_data(id_metadata)
    d['has_resource_type'] = (
        True
        if (
            d['current_profile'].name == 'datacite'
            and 'datacite.resourcetype' in id_metadata
            and id_metadata['datacite.resourcetype'] != ''
        )
        else False
    )
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, "manage/details", d)


def display_xml(request, identifier):
    """Used for displaying DataCite or Crossref XML."""
    d = {'menu_item': 'ui_manage.null'}
    r = _getLatestMetadata(identifier, request)
    if type(r) is str:
        django.contrib.messages.error(request, impl.ui_common.formatError(r))
        return django.shortcuts.redirect("/")
    s, id_metadata = r
    assert s.startswith("success:")
    d['identifier'] = id_metadata
    d['current_profile'] = impl.metadata.getProfile(id_metadata['_profile'])
    if d['current_profile'].name == 'datacite' and 'datacite' in id_metadata:
        content = id_metadata["datacite"]
    elif d['current_profile'].name == 'crossref' and 'crossref' in id_metadata:
        content = id_metadata["crossref"]
    else:
        return impl.ui_common.staticTextResponse("No XML metadata.")

    # By setting the content type ourselves, we gain control over the
    # character encoding and can properly set the content length.
    ec = content.encode("utf-8")
    r = django.http.HttpResponse(ec, content_type="application/xml; charset=utf-8")
    r["Content-Length"] = len(ec)
    return r


def _isTestId(id_text, testPrefixes):
    for pre in testPrefixes:
        if id_text.startswith(pre['prefix']):
            return True
    return False


@impl.ui_common.user_login_required
def download(request):
    """Enqueue a batch download request and display link to user."""
    d = {'menu_item': 'ui_manage.null'}
    q = django.http.QueryDict(
        "format=csv&convertTimestamps=yes&compression=zip", mutable=True
    )
    q.setlist(
        'column',
        [
            "_mappedTitle",
            "_mappedCreator",
            "_id",
            "_owner",
            "_created",
            "_updated",
            "_status",
            "_target",
        ],
    )

    # In case you only want to download IDs based on owner selection:
    # username = impl.ui_common.getOwnerOrGroup(request.GET['owner_selected'])
    # q['owner'] = ezidapp.models.user.User.objects.get(name=username)
    user = impl.userauth.getUser(request)
    q['notify'] = d['mail'] = user.accountEmail
    # ToDo make changes to download.enqueueRequest() to accept multiple groups
    # if user.isRealmAdministrator: q['ownergroup'] = [g.groupname for g in user.realm.groups.all()]
    if user.isGroupAdministrator:
        q['ownergroup'] = user.group.groupname
    else:
        q['owner'] = user.username
    s = impl.download.enqueueRequest(user, q)
    if not s.startswith("success:"):
        django.contrib.messages.error(request, s)
        return django.shortcuts.redirect("ui_manage.index")
    else:
        d['link'] = s.split()[1]
    # noinspection PyUnresolvedReferences
    return impl.ui_common.render(request, "manage/download", d)


def download_error(request):
    """Download link error."""
    # . Translators: Copy HTML tags over and only translate words outside of these tags
    # . i.e.: <a class="don't_translate_class_names" href="don't_translate_urls">Translate this text</a>
    content = [
        _("If you have recently requested a batch download of your identifiers, ")
        + _(
            "the file may not be complete. Please close this window, then try the download "
        )
        + _("link again in a few minutes."),
        _("If you are trying to download a file of identifiers from a link that was ")
        + _("generated over seven days ago, the download link has expired. Go to ")
        + "<a class='link__primary' href='/manage'>"
        + _("Manage IDs")
        + "</a> "
        + _("and click &quot;Download All&quot; to generate a new download link."),
        _("Please <a class='link__primary' href='/contact'>contact us</a> if you need ")
        + _("assistance."),
    ]
    return impl.ui_common.error(request, 404, content)
