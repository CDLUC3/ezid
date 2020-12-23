import logging

import django.apps
import django.db.utils

logger = logging.getLogger(__name__)


class Startup(django.apps.AppConfig):
    name = "ezidapp"


    def ready(self):
        logging.debug('impl.startup: START')

        try:
            from . import config
            config.load()

            import ezidapp.models.shoulder
            ezidapp.models.shoulder.loadConfig()
            config.registerReloadListener(ezidapp.models.shoulder.loadConfig)

            from . import util2
            util2.loadConfig()
            config.registerReloadListener(util2.loadConfig)

            from . import ui_common
            ui_common.loadConfig()
            config.registerReloadListener(ui_common.loadConfig)
        except Exception:
            # App not ready to be configured yet. This allows running
            # `django-admin migrate` to create the initial databases.
            logging.debug('impl.startup: Early exit: App not ready yet')
            return

        from . import log
        log.loadConfig()
        config.registerReloadListener(log.loadConfig)

        from . import backproc
        config.registerReloadListener(backproc.loadConfig)
        backproc.loadConfig()

        from . import binder_async
        binder_async.loadConfig()
        config.registerReloadListener(binder_async.loadConfig)

        from . import crossref
        crossref.loadConfig()
        config.registerReloadListener(crossref.loadConfig)

        from . import datacite
        datacite.loadConfig()
        config.registerReloadListener(datacite.loadConfig)

        from . import datacite_async
        datacite_async.loadConfig()
        config.registerReloadListener(datacite_async.loadConfig)

        from . import download
        download.loadConfig()
        config.registerReloadListener(download.loadConfig)

        from . import ezid
        ezid.loadConfig()
        config.registerReloadListener(ezid.loadConfig)

        from . import linkcheck_update
        linkcheck_update.loadConfig()
        config.registerReloadListener(linkcheck_update.loadConfig)

        from . import metadata
        metadata.loadConfig()
        config.registerReloadListener(metadata.loadConfig)

        from . import newsfeed
        newsfeed.loadConfig()
        config.registerReloadListener(newsfeed.loadConfig)

        from . import noid_egg
        noid_egg.loadConfig()
        config.registerReloadListener(noid_egg.loadConfig)

        from . import noid_nog
        noid_nog.loadConfig()
        config.registerReloadListener(noid_nog.loadConfig)

        from . import oai
        oai.loadConfig()
        config.registerReloadListener(oai.loadConfig)

        from . import search_util
        search_util.loadConfig()
        config.registerReloadListener(search_util.loadConfig)

        from . import stats
        stats.loadConfig()
        config.registerReloadListener(stats.loadConfig)

        from . import status
        status.loadConfig()
        config.registerReloadListener(status.loadConfig)

        logging.debug('impl.startup: END')
