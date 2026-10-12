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

