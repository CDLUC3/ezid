# =============================================================================
#
# EZID :: policy.py
#
# Authorization policy.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2010, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import ldap
import re
import threading

import config

_lock = threading.Lock()
_prefixes = None
_nonTestLabels = None
_groups = None
_ldapEnabled = None
_ldapServer = None
_userDnTemplate = None
_adminUsername = None
_adminPassword = None

def _loadConfig ():
  global _prefixes, _nonTestLabels, _groups, _ldapEnabled, _ldapServer
  global _userDnTemplate, _adminUsername, _adminPassword
  _lock.acquire()
  try:
    _prefixes = dict([k, config.config("prefix_%s.prefix" % k)]\
      for k in config.config("prefixes.keys").split(","))
    _nonTestLabels = ",".join(k for k in\
      config.config("prefixes.keys").split(",") if not k.startswith("TEST"))
    _groups = {}
    _ldapEnabled = (config.config("ldap.enabled").lower() == "true")
    _ldapServer = config.config("ldap.server")
    _userDnTemplate = config.config("ldap.user_dn_template")
    _adminUsername = config.config("ldap.admin_username")
    _adminPassword = config.config("ldap.admin_password")
  finally:
    _lock.release()

_loadConfig()
config.addLoader(_loadConfig)

def _loadPrefixesLdap (group):
  l = None
  try:
    l = ldap.initialize(_ldapServer)
    l.bind_s(_userDnTemplate % _adminUsername, _adminPassword,
      ldap.AUTH_SIMPLE)
    r = l.search_s(group[2], ldap.SCOPE_BASE)
    assert len(r) == 1 and r[0][0] == group[2] and\
      "ezidGroup" in r[0][1]["objectClass"] and\
      len(r[0][1]["shoulderList"]) == 1,\
      "unexpected return from LDAP search command, DN='%s'" % group[2]
    # Although not documented anywhere, it appears that returned
    # values are UTF-8 encoded.
    return r[0][1]["shoulderList"][0].decode("UTF-8")
  finally:
    if l: l.unbind()

def _loadPrefixesLocal (group):
  return config.config("group_%s.prefixes" % group[0])

def _loadPrefixes (group):
  if group[0] == _adminUsername:
    l = _nonTestLabels
  elif group[0] == "anonymous":
    l = ""
  elif _ldapEnabled:
    l = _loadPrefixesLdap(group)
  else:
    l = _loadPrefixesLocal(group)
  return [_prefixes[k] for k in re.split("[, ]+", l) if len(k) > 0]

def _getPrefixes (group):
  _lock.acquire()
  try:
    if group in _groups:
      return _groups[group]
    else:
      _groups[group] = _loadPrefixes(group)
      return _groups[group]
  finally:
    _lock.release()

def getPrefixes (user, group):
  """
  Returns a list of the prefixes available to a user not including the
  test prefixes.  'user' and 'group' should each be authenticated
  (local name, persistent identifier) tuples, e.g., ("dryad",
  "ark:/13030/foo").  Throws an exception on error.
  """
  return _getPrefixes(group)[:]

def authorizeCreate (user, group, prefix):
  """
  Returns true if a request to mint or create an identifier is
  authorized.  'user' and 'group' should each be authenticated (local
  name, persistent identifier) tuples, e.g., ("dryad",
  "ark:/13030/foo").  'prefix' may be a complete identifier or just a
  prefix of one; in either case it must be qualified, e.g.,
  "doi:10.5060/".  Throws an exception on error.
  """
  return prefix.startswith(_prefixes["TESTARK"]) or\
    prefix.startswith(_prefixes["TESTDOI"]) or\
    len(filter(lambda p: prefix.startswith(p), _getPrefixes(group))) > 0

def authorizeUpdate (rUser, rGroup, identifier, iUser, iGroup):
  """
  Returns true if a request to update an existing identifier is
  authorized.  'rUser' and 'rGroup' identify the requester and should
  each be authenticated (local name, persistent identifier) tuples,
  e.g., ("dryad", "ark:/13030/foo"); 'iUser' and 'iGroup' should be
  similar quantities that identify the identifier's owner.
  'identifier' is the identifier in question; it must be qualified, as
  in "doi:10.5060/foo".  Throws an exception on error.
  """
  return rUser[:2] == iUser or rUser[0] == _adminUsername
