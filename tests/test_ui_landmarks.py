import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory

import impl.metadata
import impl.ui_common
import impl.ui_search


@pytest.mark.django_db
def test_public_pages_landmarks():
    client = Client()
    for path in ['/', '/search', '/contact']:
        response = client.get(path)
        assert response.status_code == 200, f"Failed GET for {path}"
        html = response.content.decode('utf-8')

        # Audit row 5: exactly one main landmark
        assert html.count('<main') == 1, f"Expected 1 main landmark on {path}, found {html.count('<main')}"
        assert '<main id="main-content">' in html, f"Main landmark missing id='main-content' on {path}"
        assert '</main>' in html, f"Missing closing main tag on {path}"

        # Audit row 7: banner and footer landmarks present
        assert '<header role="banner">' in html, f"Missing banner header on {path}"
        assert '<footer class="footer">' in html, f"Missing footer landmark on {path}"
        assert 'aria-label="Main"' in html, f"Missing Main nav label on {path}"

        # Audit row 19: no native nav repeats role="navigation"
        assert '<nav role="navigation"' not in html, f"Native nav has redundant role on {path}"
        assert '<nav id="js-header__nav"' in html, f"Missing header nav on {path}"

        # Audit rows 11, 23, 53: native form elements do not repeat role="form"
        assert '<form' in html, f"Missing form on {path}"
        assert 'role="form"' not in html and "role='form'" not in html, f"Native form has redundant role on {path}"

        # Audit rows 9 and 38: Learn submenu is a named nav region with links grouped in a list
        assert '<nav class="header__subnav-panel" aria-label="Learn">' in html, f"Learn submenu missing nav landmark on {path}"
        assert '<ul class="header__subnav-list">' in html, f"Learn submenu links should be in a list on {path}"

        # Audit rows 10 and 16: Footer navigation links grouped in a list within a named nav landmark
        assert '<nav aria-label="Footer">' in html, f"Footer missing nav landmark on {path}"
        assert '<ul class="footer__copyright-links">' in html, f"Footer links should be in a list on {path}"

        # Audit row 22: RSS link appears after other footer links in DOM and keyboard focus order
        rss_pos = html.find('class="footer__icon-link"')
        footer_links_pos = html.find('class="footer__copyright-links"')
        assert rss_pos != -1 and footer_links_pos != -1, f"Missing RSS or footer links on {path}"
        assert rss_pos > footer_links_pos, f"RSS link should appear after other footer links on {path}"


@pytest.mark.django_db
def test_authenticated_user_navigation_landmark():
    rf = RequestFactory()
    request = rf.get('/search')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    setattr(request, '_messages', FallbackStorage(request))

    class MockUser:
        username = 'testadmin'

    d = {
        'menu_item': 'ui_account.null',
        'authenticatedUser': MockUser(),
        'form': [],
    }
    response = impl.ui_common.render(request, 'account/pwreset1', d)
    assert response.status_code == 200
    html = response.content.decode('utf-8')

    # Admin greeting is inside header banner
    assert '<header role="banner">' in html
    assert 'Welcome testadmin!' in html
    admin_pos = html.find('Welcome testadmin!')
    header_start = html.find('<header role="banner">')
    header_end = html.find('</header>')
    assert header_start < admin_pos < header_end, "Welcome admin text should be inside header banner landmark"

    # Audit row 37: Logged-in account menu is a named navigation region
    assert '<nav class="login-menu__container" aria-label="Account menu">' in html
    assert html.count('<main') == 1


def test_id_details_page_landmarks_and_sections():
    rf = RequestFactory()
    request = rf.get('/id/ark:/99999/fk4test')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    setattr(request, '_messages', FallbackStorage(request))

    internal_profile = impl.metadata.getProfile('internal')
    datacite_profile = impl.metadata.getProfile('datacite')

    d = {
        'menu_item': 'ui_manage.null',
        'testPrefixes': {},
        'id_text': 'ark:/99999/fk4test',
        'id_as_url': 'https://ezid.cdlib.org/id/ark:/99999/fk4test',
        'identifier': {'_target': 'http://example.com'},
        'internal_profile': internal_profile,
        'current_profile': datacite_profile,
        'pub_status': 'public',
        'allow_update': True,
        'has_block_data': False,
        'has_resource_type': False,
        'stat_reason': '',
        'recent_creation': False,
        'recent_update': False,
        'is_test_id': True,
    }

    response = impl.ui_common.render(request, 'manage/details', d)
    assert response.status_code == 200
    html = response.content.decode('utf-8')

    # Audit row 5: exactly one main landmark
    assert html.count('<main') == 1
    assert '<main id="main-content">' in html

    # Audit row 120: ID Details sections with headings grouped in landmarks
    assert '<section aria-labelledby="about-identifier-heading">' in html
    assert '<h2 id="about-identifier-heading"' in html
    assert '<section class="row vertical-buffer-20" aria-labelledby="citation-preview-heading">' in html
    assert '<h2 id="citation-preview-heading"' in html
    assert '<section aria-labelledby="about-object-heading">' in html
    assert '<h2 id="about-object-heading"' in html
    assert '<section aria-labelledby="about-status-heading">' in html
    assert '<h2 id="about-status-heading"' in html


@pytest.mark.django_db
def test_breadcrumb_navigation_landmarks():
    client = Client()
    # Audit rows 59, 60, 71, 72, 76, 77, 92, 93, 98, 99:
    # Breadcrumbs on FAQ, Open Source, API Guide, ID Basics, and Suffix Passthrough
    doc_pages = [
        '/learn/doi_services_faq',
        '/learn/open_source',
        '/doc/apidoc.html',
        '/learn/id_basics',
        '/learn/suffix_passthrough',
    ]
    for path in doc_pages:
        response = client.get(path)
        assert response.status_code == 200, f"Failed GET for {path}"
        html = response.content.decode('utf-8')

        # Navigation landmark named "Breadcrumb"
        assert '<nav aria-label="Breadcrumb">' in html, f"Missing Breadcrumb nav landmark on {path}"

        # Valid list markup within the breadcrumb navigation landmark
        breadcrumb_nav_pos = html.find('<nav aria-label="Breadcrumb">')
        breadcrumb_nav_end = html.find('</nav>', breadcrumb_nav_pos)
        breadcrumb_snippet = html[breadcrumb_nav_pos:breadcrumb_nav_end]
        assert '<ul class="breadcrumb">' in breadcrumb_snippet, f"Breadcrumb items must be in a list on {path}"

        # Final breadcrumb item identifies current page
        assert 'aria-current="page"' in breadcrumb_snippet, f"Missing aria-current='page' on {path}"
        assert '<li class="active" aria-current="page">' in breadcrumb_snippet, (
            f"Final active breadcrumb item must have aria-current='page' on {path}"
        )

        # No duplicate navigation labels on the page
        import re
        nav_labels = re.findall(r'<nav[^>]*aria-label="([^"]+)"', html)
        assert len(nav_labels) == len(set(nav_labels)), f"Duplicate nav aria-labels found on {path}: {nav_labels}"


def test_search_results_forms_redundant_roles():
    rf = RequestFactory()
    request = rf.get('/search/results?keywords=test')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    setattr(request, '_messages', FallbackStorage(request))

    d = {
        'menu_item': 'ui_search.null',
        'heading_title': 'Search Results',
        'search_query': 'test',
        'REQUEST': request.GET,
        'results': [{'c_identifier': 'ark:/99999/fk4test', 'c_title': 'Test Title'}],
        'total_results': 25,
        'total_pages': 3,
        'page_sizes': [10, 20, 50, 100],
        'ps': 10,
        'p': 1,
        'order_by': 'c_title',
        'sort': 'asc',
        'fields_selected': ['c_title', 'c_identifier'],
        'field_order': ['c_title', 'c_identifier'],
        'fields_mapped': impl.ui_search.FIELDS_MAPPED,
        'field_display_types': impl.ui_search.FIELD_DISPLAY_TYPES,
        'testPrefixes': {},
        'filtered': True,
    }
    response = impl.ui_common.render(request, 'search/results', d)
    assert response.status_code == 200
    html = response.content.decode('utf-8')

    # Audit rows 39 through 50: Results forms
    # Including #return-to-search, #ps-top, #p-top, table-column forms, #ps-bottom, and #p-bottom
    assert '<form method="get" action="/search" id="return-to-search">' in html
    assert 'id="ps-top"' in html
    assert 'id="p-top"' in html
    assert 'id="ps-bottom"' in html
    assert 'id="p-bottom"' in html
    assert 'role="form"' not in html
    assert "role='form'" not in html


def test_dashboard_forms_redundant_roles():
    rf = RequestFactory()
    request = rf.get('/dashboard')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    setattr(request, '_messages', FallbackStorage(request))

    d = {
        'menu_item': 'ui_admin.dashboard',
        'heading_user_display': "TestUser's EZID Dashboard",
        'totals': [],
        'has_broken_links': False,
        'results_crossref': [{'c_identifier': 'ark:/99999/fk4test', 'c_crossref_date': '2026-01-01', 'c_crossref_descr': 'test', 'c_crossref_msg': 'test'}],
        'results_issues': [{'c_identifier': 'ark:/99999/fk4test', 'c_id_issue': 'bad link', 'c_title': 'Test', 'c_update_time': '2026-01-01'}],
        's_type': 'issues',
        'total_pages_issues': 2,
        'total_pages_crossref': 2,
        'REQUEST': request.GET,
        'p': 1,
        'ps': 10,
        'display_adminlink': True,
        'months_all': ['2026-01', '2026-02'],
        'month_from': '2026-01',
        'month_to': '2026-02',
    }
    response = impl.ui_common.render(request, 'dashboard/index', d)
    assert response.status_code == 200
    html = response.content.decode('utf-8')

    # Audit row 109: Dashboard #p_issues
    assert 'id="p_issues"' in html
    assert 'id="usage_form"' in html
    assert 'role="form"' not in html
    assert "role='form'" not in html


@pytest.mark.django_db
def test_search_and_results_accessible_fieldsets_and_page_sizes():
    client = Client()
    response = client.get('/search')
    assert response.status_code == 200
    html = response.content.decode('utf-8')

    # Audit row 26: Search .fieldset-stacked inputs should be grouped in a fieldset
    assert '<fieldset class="fieldset-stacked">' in html
    assert '<legend class="fieldset-stacked__legend search__publication-fieldset">' in html
    assert 'Object Publication Year' in html
    assert '<div class="fieldset-stacked" role="group"' not in html

    rf = RequestFactory()
    request = rf.get('/search/results?keywords=test')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    setattr(request, '_messages', FallbackStorage(request))

    d = {
        'menu_item': 'ui_search.null',
        'heading_title': 'Search Results',
        'search_query': 'test',
        'REQUEST': request.GET,
        'results': [{'c_identifier': 'ark:/99999/fk4test', 'c_title': 'Test Title'}],
        'total_results': 25,
        'total_pages': 3,
        'page_sizes': [10, 20, 50, 100],
        'ps': 10,
        'p': 1,
        'order_by': 'c_title',
        'sort': 'asc',
        'fields_selected': ['c_title', 'c_identifier'],
        'field_order': ['c_title', 'c_identifier'],
        'fields_mapped': impl.ui_search.FIELDS_MAPPED,
        'field_display_types': impl.ui_search.FIELD_DISPLAY_TYPES,
        'testPrefixes': {},
        'filtered': True,
    }
    response = impl.ui_common.render(request, 'search/results', d)
    assert response.status_code == 200
    results_html = response.content.decode('utf-8')

    # Audit rows 34 and 35: Results #ps-top and #ps-bottom selects have single "Results per page" label
    assert '<label for="page-size-top" class="pagination__select-label">Results per page</label>' in results_html
    assert '<label for="page-size-bottom" class="pagination__select-label">Results per page</label>' in results_html
    assert 'aria-label="Results per page"' in results_html
    assert 'class="search-results__select-appended-text"' not in results_html
    assert 'Show number of entries' not in results_html


def test_manage_accessible_fieldsets_and_page_sizes():
    import impl.form_objects

    rf = RequestFactory()
    request = rf.get('/manage')
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    setattr(request, '_messages', FallbackStorage(request))

    class MockUser:
        username = 'testadmin'

    d = {
        'menu_item': 'ui_manage.null',
        'authenticatedUser': MockUser(),
        'form': impl.form_objects.ManageSearchIdForm({}),
        'collapse_advanced_search': 'expanded',
        'total_results_str': '25',
        'total_results': 25,
        'total_pages': 3,
        'page_sizes': [10, 20, 50, 100],
        'ps': 10,
        'p': 1,
        'order_by': 'c_update_time',
        'sort': 'asc',
        'fields_selected': ['c_title', 'c_identifier'],
        'field_order': ['c_title', 'c_identifier'],
        'fields_mapped': impl.ui_search.FIELDS_MAPPED,
        'field_display_types': impl.ui_search.FIELD_DISPLAY_TYPES,
        'results': [{'c_identifier': 'ark:/99999/fk4test', 'c_title': 'Test Title'}],
        'testPrefixes': {},
        'REQUEST': request.GET,
        'filtered': True,
        'owner_selected': '',
    }
    response = impl.ui_common.render(request, 'manage/index', d)
    assert response.status_code == 200
    html = response.content.decode('utf-8')

    # Audit rows 114 and 115: Manage #ps-top and #ps-bottom selects have single "Results per page" label
    assert '<label for="page-size-top" class="pagination__select-label">Results per page</label>' in html
    assert '<label for="page-size-bottom" class="pagination__select-label">Results per page</label>' in html
    assert 'aria-label="Results per page"' in html
    assert 'class="search-results__select-appended-text"' not in html
    assert 'Show number of entries' not in html

    # Audit rows 117 and 118: Two Manage radio-button groups are contained in fieldsets
    # Harvesting radio group
    harvesting_pos = html.find('manage__form-element-container--harvesting')
    assert harvesting_pos != -1
    harvesting_snippet = html[harvesting_pos : harvesting_pos + 1000]
    assert '<fieldset class="fieldset-stacked">' in harvesting_snippet
    assert '<legend class="fieldset-stacked__legend manage__fieldset-legend">' in harvesting_snippet
    assert '</fieldset>' in harvesting_snippet

    # Has Metadata radio group
    metadata_pos = html.find('Has Metadata?')
    assert metadata_pos != -1
    metadata_snippet = html[metadata_pos - 150 : metadata_pos + 800]
    assert '<fieldset class="fieldset-stacked">' in metadata_snippet
    assert '<legend class="fieldset-stacked__legend manage__fieldset-legend">' in metadata_snippet
    assert '</fieldset>' in metadata_snippet

    # Control groups in Manage use valid fieldset and legend markup
    assert html.count('<fieldset class="fieldset-stacked') >= 5
    assert '<div class="fieldset-stacked" role="group"' not in html
    assert '<div class="fieldset-stacked manage_fieldset" role="group"' not in html
    assert '<div class="fieldset-stacked manage__fieldset" role="group"' not in html


@pytest.mark.django_db
def test_accessible_links_home_learn_open_source_and_api_guide():
    client = Client()

    # Audit row 18: Links in the EZID Home "Learn" section are valid links discoverable by assistive technology
    resp_home = client.get('/')
    assert resp_home.status_code == 200
    home_html = resp_home.content.decode('utf-8')
    assert 'class="home-banner__lead-button"' in home_html
    assert 'href="/learn/"' in home_html or 'href="/learn"' in home_html
    assert 'Learn more about EZID' in home_html
    # Submenu Learn links have valid destinations
    for href in ['/learn/#01', '/learn/#02', '/learn/#04', '/learn/#05', '/learn/doi_services_faq', '/doc/apidoc.html', '/demo']:
        assert f'href="{href}"' in home_html

    # Audit rows 61 and 62: Two links in Learn accordion section 01 match underlined text-link style (link__primary)
    resp_learn = client.get('/learn/')
    assert resp_learn.status_code == 200
    learn_html = resp_learn.content.decode('utf-8')
    assert '<a class="link__primary" href="https://dmptool.org" target="_blank">DMP Tool</a>' in learn_html
    assert '<a class="link__primary" href="https://www.go-fair.org/fair-principles/" target="_blank">' in learn_html

    # Audit row 73: Open Source page consolidates wording around one clear contact link
    resp_os = client.get('/learn/open_source')
    assert resp_os.status_code == 200
    os_html = resp_os.content.decode('utf-8')
    assert 'If you are the author of a resource listed here and you wish us to remove it, or if you are the author of software that you wish to be listed' in os_html
    assert 'please <a class="link__primary" href="/contact">contact us</a>.' in os_html
    # Only one contact us link in the intro section
    intro_start = os_html.find('<strong>IMPORTANT:</strong>')
    assert intro_start != -1
    intro_end = os_html.find('<ul>', intro_start)
    assert intro_end != -1
    intro_snippet = os_html[intro_start:intro_end]
    assert intro_snippet.count('href="/contact"') == 1

    # Audit row 85: The API Guide link under #metadata-requirements-mapping resolves to intended destination
    resp_api = client.get('/doc/apidoc.html')
    assert resp_api.status_code == 200
    api_html = resp_api.content.decode('utf-8')
    assert 'https://wiki.ucop.edu/display/Curation/ERC' not in api_html
    mapping_idx = api_html.find('id="metadata-requirements-mapping"')
    assert mapping_idx != -1
    next_section_idx = api_html.find('id="crossref-registration"', mapping_idx)
    assert next_section_idx != -1
    mapping_snippet = api_html[mapping_idx:next_section_idx]
    assert 'href="https://www.dublincore.org/groups/kernel/spec/"' in mapping_snippet
    assert 'Kernel Metadata' in mapping_snippet
    assert 'href="https://arks.org/specs/"' in api_html
    assert '{{' not in api_html
    assert '}}' not in api_html

