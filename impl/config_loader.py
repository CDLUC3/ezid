# =============================================================================
#
# EZID :: config_loader.py
#
# Low-level configuration file loader, for use by config.py and Django
# configuration files only.  Regarding the latter, note that this
# module does *not* import any Django classes, and hence can itself be
# imported by Django to obtain database passwords and such without
# encountering circular import problems.
#
# Author:
#   Greg Janee <gjanee@ucop.edu>
#
# License:
#   Copyright (c) 2015, Regents of the University of California
#   http://creativecommons.org/licenses/BSD/
#
# -----------------------------------------------------------------------------

import configparser
import os.path


class Config(object):
    """Holds the contents of the EZID configuration files."""

    def __init__(
        self, siteRoot, projectRoot, configFile, shadowConfigFile, deploymentLevel
    ):
        self._config = configparser.ConfigParser(
            {"SITE_ROOT": siteRoot, "PROJECT_ROOT": projectRoot}
        )
        f = open(configFile)
        self._config.readfp(f)
        f.close()
        self._shadowConfig = configparser.ConfigParser()
        if os.path.exists(shadowConfigFile):
            f = open(shadowConfigFile)
            self._shadowConfig.readfp(f)
            f.close()
        self._level = "{%s}" % deploymentLevel

    def getOption(self, option):
        """Returns the value of a configuration option.

        The option name should be specified in section.option syntax,
        e.g., "datacite.username".
        """
        s, o = option.split(".")
        if self._shadowConfig.has_option(s, self._level + o):
            return self._shadowConfig.get(s, self._level + o)
        elif self._config.has_option(s, self._level + o):
            return self._config.get(s, self._level + o)
        elif self._shadowConfig.has_option(s, o):
            return self._shadowConfig.get(s, o)
        else:
            return self._config.get(s, o)
