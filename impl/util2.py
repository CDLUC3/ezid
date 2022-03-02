#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Utility functions that require that EZID's configuration be loaded
"""

import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import django.conf


def urlForm(identifier):
    """Return the URL form of a qualified identifier, or "[None]" if there is
    no resolver defined for the identifier type."""
    if identifier.startswith("doi:"):
        return f"{django.conf.settings.RESOLVER_DOI}/{urllib.parse.quote(identifier[4:], ':/')}"
    elif identifier.startswith("ark:/"):
        return f"{django.conf.settings.RESOLVER_ARK}/{urllib.parse.quote(identifier, ':/')}"
    else:
        return "[None]"


def defaultTargetUrl(identifier):
    """Return the default target URL for an identifier

    The identifier is assumed to be in normalized, qualified form.
    """
    return f"{django.conf.settings.DEFAULT_TARGET_BASE_URL}/id/{urllib.parse.quote(identifier, ':/')}"


def tombstoneTargetUrl(identifier):
    """Return the "tombstone" target URL for an identifier

    The identifier is assumed to be in normalized, qualified form.
    """
    return f"{django.conf.settings.EZID_BASE_URL}/tombstone/id/{urllib.parse.quote(identifier, ':/')}"


def isTestIdentifier(identifier):
    """Return True if the supplied qualified identifier is a test
    identifier."""
    return (
        identifier.startswith(django.conf.settings.SHOULDERS_ARK_TEST)
        or identifier.startswith(django.conf.settings.SHOULDERS_DOI_TEST)
        or identifier.startswith(django.conf.settings.SHOULDERS_CROSSREF_TEST)
    )


def isTestArk(identifier):
    """Returns True if the supplied unqualified ARK (e.g., "12345/foo") is a
    test identifier."""
    return identifier.startswith(django.conf.settings.SHOULDERS_ARK_TEST[5:])


def isTestDoi(identifier):
    """Returns True if the supplied unqualified DOI (e.g., "10.1234/FOO") is a
    test identifier."""
    return identifier.startswith(django.conf.settings.SHOULDERS_DOI_TEST[4:])


def isTestCrossrefDoi(identifier):
    """Returns True if the supplied unqualified DOI (e.g., "10.1234/FOO") is a
    Crossref test identifier."""
    return identifier.startswith(django.conf.settings.SHOULDERS_CROSSREF_TEST[4:])
