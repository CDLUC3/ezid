import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory

import impl.metadata
import impl.ui_common


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
