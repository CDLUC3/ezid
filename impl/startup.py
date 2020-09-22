import logging

import django.apps
import django.db.utils

logger = logging.getLogger(__name__)


class Startup(django.apps.AppConfig):
    name = "ezidapp"

    def ready(self):
        # logging.debug('impl.startup START')

        try:
            import config
            config.load()

            import ezidapp.models.shoulder
            ezidapp.models.shoulder.loadConfig()
            config.registerReloadListener(ezidapp.models.shoulder.loadConfig)

            import util2
            util2.loadConfig()
            config.registerReloadListener(util2.loadConfig)

            import ui_common
            ui_common.loadConfig()
            config.registerReloadListener(ui_common.loadConfig)
        except Exception:
            # App not ready to be configured yet. This allows running
            # `django-admin migrate` to create the initial databases.
            return

        import log
        log.loadConfig()
        config.registerReloadListener(log.loadConfig)

        import backproc
        config.registerReloadListener(backproc.loadConfig)
        backproc.loadConfig()

        import binder_async
        binder_async.loadConfig()
        config.registerReloadListener(binder_async.loadConfig)

        import crossref
        crossref.loadConfig()
        config.registerReloadListener(crossref.loadConfig)

        import datacite
        datacite.loadConfig()
        config.registerReloadListener(datacite.loadConfig)

        import datacite_async
        datacite_async.loadConfig()
        config.registerReloadListener(datacite_async.loadConfig)

        import download
        download.loadConfig()
        config.registerReloadListener(download.loadConfig)

        import ezid
        ezid.loadConfig()
        config.registerReloadListener(ezid.loadConfig)

        import linkcheck_update
        linkcheck_update.loadConfig()
        config.registerReloadListener(linkcheck_update.loadConfig)

        import metadata
        metadata.loadConfig()
        config.registerReloadListener(metadata.loadConfig)

        import newsfeed
        newsfeed.loadConfig()
        config.registerReloadListener(newsfeed.loadConfig)

        import noid_egg
        noid_egg.loadConfig()
        config.registerReloadListener(noid_egg.loadConfig)

        import noid_nog
        noid_nog.loadConfig()
        config.registerReloadListener(noid_nog.loadConfig)

        import oai
        oai.loadConfig()
        config.registerReloadListener(oai.loadConfig)

        import search_util
        search_util.loadConfig()
        config.registerReloadListener(search_util.loadConfig)

        import stats
        stats.loadConfig()
        config.registerReloadListener(stats.loadConfig)

        import status
        status.loadConfig()
        config.registerReloadListener(status.loadConfig)

        # logging.debug('impl.startup END')
