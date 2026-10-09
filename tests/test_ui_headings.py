import re
import pytest
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory

import impl.ui_common


@pytest.mark.django_db
def test_home_page_headings_and_note():
    client = Client()
    response = client.get('/')
    assert response.status_code == 200
    html = response.content.decode('utf-8')

    # Audit row 6: EZID Home has one descriptive level-one heading
    h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    assert len(h1_matches) == 1, f"Expected 1 h1 on Home, found {len(h1_matches)}"
    assert 'EZID:' in h1_matches[0]
    # Ensure it is not display: none
    h1_tag = re.search(r'<h1[^>]*>', html).group(0)
    assert 'display: none' not in h1_tag
    assert 'visually-hidden' in h1_tag

    # Audit row 17: EZID Home "Note" label does not use <b> element
    assert '<b>NOTE:</b>' not in html
    assert '<strong class="home__identifier-lead-note-label">NOTE:</strong>' in html


@pytest.mark.django_db
def test_learn_page_heading_hierarchy():
    client = Client()
    response = client.get('/learn/')
    assert response.status_code == 200
    html = response.content.decode('utf-8')

    # Exactly one h1
    h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    assert len(h1_matches) == 1

    # Audit row 63: Current users is an h3 to preserve heading hierarchy
    assert '<h3 class="heading_3">Current users</h3>' in html
    assert '<h4 class="heading_3">Current users</h4>' not in html


@pytest.mark.django_db
def test_api_guide_headings_and_batch_download():
    client = Client()
    for path in ['/doc/apidoc.html', '/doc/apidoc.2.html']:
        response = client.get(path)
        assert response.status_code == 200, f"Failed GET for {path}"
        html = response.content.decode('utf-8')

        # Audit row 88: The API Guide has exactly one h1; section headings are h2
        h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
        assert len(h1_matches) == 1, f"Expected exactly 1 h1 on {path}, found {len(h1_matches)}"
        assert 'The EZID API' in h1_matches[0]

        # Section headings are h2
        assert '<h2>Contents</h2>' in html
        assert '<h2>Framework</h2>' in html
        assert '<h2>Batch download</h2>' in html
        assert '<h2>OAI-PMH harvesting</h2>' in html

        # Audit row 87: batch-download subsections are headings (h3)
        assert '<h3 id="overview">Overview</h3>' in html
        assert '<h3 id="download-formats">Download formats</h3>' in html
        assert '<h3 id="parameters">Parameters</h3>' in html
        assert '<h3 id="using-curl-to-request-a-download">Using curl to request a download</h3>' in html

        # Ensure they are no longer paragraph tags
        assert '<p id="overview"><strong>Overview</strong></p>' not in html
        assert '<p id="download-formats"><strong>Download formats</strong></p>' not in html


def test_dashboard_heading_structure():
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
        'results_crossref': [],
    }
    response = impl.ui_common.render(request, 'dashboard/index', d)
    assert response.status_code == 200
    html = response.content.decode('utf-8')

    # Audit row 108: Dashboard has one descriptive level-one heading
    h1_matches = re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    assert len(h1_matches) == 1, f"Expected 1 h1 on Dashboard, found {len(h1_matches)}"
    assert "TestUser's EZID Dashboard" in h1_matches[0]
    h1_tag = re.search(r'<h1[^>]*>', html).group(0)
    assert 'visually-hidden' in h1_tag
    # Ensure jQuery hide() is not used on heading
    assert "$('.heading__primary-container').hide()" not in html
