# import impl.util
#
#
# # from ezidapp.models.binder_queue          import BinderQueue
# from ezidapp.models.crossref_queue        import CrossrefQueue
# from ezidapp.models.datacenter            import Datacenter
# from ezidapp.models.datacite_queue        import DataciteQueue
# from ezidapp.models.download_queue        import DownloadQueue
# from ezidapp.models.group                 import Group
# from ezidapp.models.identifier            import Identifier
# from ezidapp.models.link_checker          import LinkChecker
# from ezidapp.models.new_account_worksheet import NewAccountWorksheet
# from ezidapp.models.profile               import Profile
# from ezidapp.models.realm                 import Realm
# from ezidapp.models.registration_queue    import RegistrationQueue
# from ezidapp.models.search_datacenter     import SearchDatacenter
# from ezidapp.models.search_group          import SearchGroup
# from ezidapp.models.search_identifier     import SearchIdentifier
# from ezidapp.models.search_profile        import SearchProfile
# from ezidapp.models.search_realm          import SearchRealm
# from ezidapp.models.search_user           import SearchUser
# from ezidapp.models.server_variables      import ServerVariables
# from ezidapp.models.shoulder              import Shoulder
# from ezidapp.models.statistics            import Statistics
# from ezidapp.models.store_datacenter      import StoreDatacenter
# from ezidapp.models.store_group           import StoreGroup
# from ezidapp.models.store_identifier      import StoreIdentifier
# from ezidapp.models.store_profile         import StoreProfile
# from ezidapp.models.store_realm           import StoreRealm
# from ezidapp.models.store_user            import StoreUser
# from ezidapp.models.update_queue          import UpdateQueue
# from ezidapp.models.user                  import User
#
# getAlertMessage = server_variables.getAlertMessage
# setAlertMessage = server_variables.setAlertMessage
# getOrSetSecretKey = server_variables.getOrSetSecretKey
# getAllShoulders = shoulder.getAllShoulders
# getLongestShoulderMatch = shoulder.getLongestShoulderMatch
# getExactShoulderMatch = shoulder.getExactShoulderMatch
# getArkTestShoulder = shoulder.getArkTestShoulder
# getDoiTestShoulder = shoulder.getDoiTestShoulder
# getCrossrefTestShoulder = shoulder.getCrossrefTestShoulder
# getAgentShoulder = shoulder.getAgentShoulder
# getDatacenterBySymbol = shoulder.getDatacenterBySymbol
# getDatacenterById = shoulder.getDatacenterById
# getGroupByPid = store_group.getUserByPid
# getGroupByGroupname = store_group.getGroupByGroupname
# getProfileById = store_group.getProfileById
# getUserByPid = store_user.getUserByPid
# getUserByUsername = store_user.getUserByUsername
# getUserById = store_user.getUserById
# getAdminUser = store_user.getAdminUser
# getProfileByLabel = store_profile.getProfileByLabel
# getProfileById = store_profile.getProfileById
#
#
# from ezidapp.models.validation import datacenterSymbol
#
#
# def getIdentifier(identifier, prefixMatch=False):
#     if prefixMatch:
#         l = list(
#             store_identifier.StoreIdentifier.objects.select_related(
#                 "owner", "owner__group", "ownergroup", "datacenter", "profile"
#             ).filter(identifier__in=impl.util.explodePrefixes(identifier))
#         )
#         if len(l) > 0:
#             return max(l, key=lambda si: len(si.identifier))
#         else:
#             raise store_identifier.StoreIdentifier.DoesNotExist()
#     else:
#         return store_identifier.StoreIdentifier.objects.select_related(
#             "owner", "owner__group", "ownergroup", "datacenter", "profile"
#         ).get(identifier=identifier)
