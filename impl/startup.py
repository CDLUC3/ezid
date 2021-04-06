import logging

import django.apps
import django.db.utils

# import django.conf

logger = logging.getLogger(__name__)


import sys


def global_exception_handler(type, value, traceback):
    logger.error('=' * 100)
    logger.error('Unhandled exception', exc_info=(type,value,traceback))
    logger.error('=' * 100)


sys.excepthook = global_exception_handler


class Startup(django.apps.AppConfig):
    name = "ezidapp"

    def ready(self):
        logger.debug('impl.startup: START')

        # try:
        import impl.config

        impl.config.load()

        import ezidapp.models.shoulder

        logger.debug("shoulder")
        try:
            ezidapp.models.shoulder.loadConfig()
            impl.config.registerReloadListener(ezidapp.models.shoulder.loadConfig)
        except Exception as e:
            logger.error(e)

        logger.debug("util2")
        import impl.util2
        impl.util2.loadConfig()
        impl.config.registerReloadListener(impl.util2.loadConfig)

        logger.debug("ui_common")
        import impl.ui_common
        try:
            impl.ui_common.loadConfig()
            impl.config.registerReloadListener(impl.ui_common.loadConfig)
        except Exception as e:
            logger.error(e)
        # except Exception:
        #     # App not ready to be configured yet. This allows running
        #     # `django-admin migrate` to create the initial databases.
        #     logging.debug('impl.startup: Early exit: App not ready yet')
        #     return

        logger.debug("log")
        import impl.log
        impl.log.loadConfig()
        impl.config.registerReloadListener(impl.log.loadConfig)

        logger.debug("backproc")
        import impl.backproc
        impl.config.registerReloadListener(impl.backproc.loadConfig)
        impl.backproc.loadConfig()

        logger.debug("binder_async")
        import impl.binder_async
        impl.binder_async.loadConfig()
        impl.config.registerReloadListener(impl.binder_async.loadConfig)

        logger.debug("crossref")
        import impl.crossref
        impl.crossref.loadConfig()
        impl.config.registerReloadListener(impl.crossref.loadConfig)

        logger.debug("datacite")
        import impl.datacite
        impl.datacite.loadConfig()
        impl.config.registerReloadListener(impl.datacite.loadConfig)

        logger.debug("datacite_async")
        import impl.datacite_async
        impl.datacite_async.loadConfig()
        impl.config.registerReloadListener(impl.datacite_async.loadConfig)

        logger.debug("download")
        import impl.download
        try:
            impl.download.loadConfig()
            impl.config.registerReloadListener(impl.download.loadConfig)
        except Exception as e:
            logger.error(e)

        logger.debug("ezid")
        import impl.ezid
        impl.ezid.loadConfig()
        impl.config.registerReloadListener(impl.ezid.loadConfig)

        logger.debug("linkcheck_update")
        import impl.linkcheck_update
        impl.linkcheck_update.loadConfig()
        impl.config.registerReloadListener(impl.linkcheck_update.loadConfig)

        logger.debug("metadata")
        import impl.metadata
        impl.metadata.loadConfig()
        impl.config.registerReloadListener(impl.metadata.loadConfig)

        logger.debug("newsfeed")
        import impl.newsfeed
        impl.newsfeed.loadConfig()
        impl.config.registerReloadListener(impl.newsfeed.loadConfig)

        logger.debug("noid_egg")
        import impl.noid_egg
        impl.noid_egg.loadConfig()
        impl.config.registerReloadListener(impl.noid_egg.loadConfig)

        logger.debug("oai")
        import impl.oai
        impl.oai.loadConfig()
        impl.config.registerReloadListener(impl.oai.loadConfig)

        logger.debug("search_util")
        import impl.search_util
        impl.search_util.loadConfig()
        impl.config.registerReloadListener(impl.search_util.loadConfig)

        logger.debug("stats")
        import impl.stats
        impl.stats.loadConfig()
        impl.config.registerReloadListener(impl.stats.loadConfig)

        logger.debug("status")
        import impl.status
        impl.status.loadConfig()
        impl.config.registerReloadListener(impl.status.loadConfig)

        logging.debug('impl.startup: END')
