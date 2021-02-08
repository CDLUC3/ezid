import logging

import django.apps
import django.db.utils

# import django.conf

logger = logging.getLogger(__name__)


import sys


def global_exception_handler(type, value, traceback):
    logger.error('=' * 100)
    logger.error('Unhandled exception:', type, value)
    import traceback

    traceback.logger.error_tb(traceback)
    logger.error('=' * 100)


sys.excepthook = global_exception_handler


class Startup(django.apps.AppConfig):
    name = "ezidapp"

    def ready(self):
        logging.debug('impl.startup: START')

        # try:
        import impl.config

        impl.config.load()

        import ezidapp.models.shoulder

        ezidapp.models.shoulder.loadConfig()
        impl.config.registerReloadListener(ezidapp.models.shoulder.loadConfig)

        import impl.util2

        impl.util2.loadConfig()
        impl.config.registerReloadListener(impl.util2.loadConfig)

        import impl.ui_common

        impl.ui_common.loadConfig()
        impl.config.registerReloadListener(impl.ui_common.loadConfig)
        # except Exception:
        #     # App not ready to be configured yet. This allows running
        #     # `django-admin migrate` to create the initial databases.
        #     logging.debug('impl.startup: Early exit: App not ready yet')
        #     return

        import impl.log

        impl.log.loadConfig()
        impl.config.registerReloadListener(impl.log.loadConfig)

        import impl.backproc

        impl.config.registerReloadListener(impl.backproc.loadConfig)
        impl.backproc.loadConfig()

        import impl.binder_async

        impl.binder_async.loadConfig()
        impl.config.registerReloadListener(impl.binder_async.loadConfig)

        import impl.crossref

        impl.crossref.loadConfig()
        impl.config.registerReloadListener(impl.crossref.loadConfig)

        import impl.datacite

        impl.datacite.loadConfig()
        impl.config.registerReloadListener(impl.datacite.loadConfig)

        import impl.datacite_async

        impl.datacite_async.loadConfig()
        impl.config.registerReloadListener(impl.datacite_async.loadConfig)

        import impl.download

        impl.download.loadConfig()
        impl.config.registerReloadListener(impl.download.loadConfig)

        import impl.ezid

        impl.ezid.loadConfig()
        impl.config.registerReloadListener(impl.ezid.loadConfig)

        import impl.linkcheck_update

        impl.linkcheck_update.loadConfig()
        impl.config.registerReloadListener(impl.linkcheck_update.loadConfig)

        import impl.metadata

        impl.metadata.loadConfig()
        impl.config.registerReloadListener(impl.metadata.loadConfig)

        import impl.newsfeed

        impl.newsfeed.loadConfig()
        impl.config.registerReloadListener(impl.newsfeed.loadConfig)

        import impl.noid_egg

        impl.noid_egg.loadConfig()
        impl.config.registerReloadListener(impl.noid_egg.loadConfig)

        import impl.noid_nog

        impl.noid_nog.loadConfig()
        impl.config.registerReloadListener(impl.noid_nog.loadConfig)

        import impl.oai

        impl.oai.loadConfig()
        impl.config.registerReloadListener(impl.oai.loadConfig)

        import impl.search_util

        impl.search_util.loadConfig()
        impl.config.registerReloadListener(impl.search_util.loadConfig)

        import impl.stats

        impl.stats.loadConfig()
        impl.config.registerReloadListener(impl.stats.loadConfig)

        import impl.status

        impl.status.loadConfig()
        impl.config.registerReloadListener(impl.status.loadConfig)

        logging.debug('impl.startup: END')
