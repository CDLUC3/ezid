import util

from binder_queue import BinderQueue
from crossref_queue import CrossrefQueue
from datacenter import Datacenter
from datacite_queue import DataciteQueue
from download_queue import DownloadQueue
from group import Group
from identifier import Identifier
from link_checker import LinkChecker
from new_account_worksheet import NewAccountWorksheet
from profile import Profile
from realm import Realm
from registration_queue import RegistrationQueue
from search_datacenter import SearchDatacenter
from search_group import SearchGroup
from search_identifier import SearchIdentifier
from search_profile import SearchProfile
from search_realm import SearchRealm
from search_user import SearchUser
from server_variables import ServerVariables
from shoulder import Shoulder, RegistrationAgency, ShoulderType
from statistics import Statistics
from store_datacenter import StoreDatacenter
from store_group import StoreGroup, AnonymousGroup
from store_identifier import StoreIdentifier
from store_profile import StoreProfile
from store_realm import StoreRealm, AnonymousRealm
from store_user import StoreUser, AnonymousUser
from update_queue import UpdateQueue
from user import User

getAlertMessage = server_variables.getAlertMessage
setAlertMessage = server_variables.setAlertMessage
getOrSetSecretKey = server_variables.getOrSetSecretKey
getAllShoulders = shoulder.getAll
getLongestShoulderMatch = shoulder.getLongestMatch
getExactShoulderMatch = shoulder.getExactMatch
getArkTestShoulder = shoulder.getArkTestShoulder
getDoiTestShoulder = shoulder.getDoiTestShoulder
getCrossrefTestShoulder = shoulder.getCrossrefTestShoulder
getAgentShoulder = shoulder.getAgentShoulder
getDatacenterBySymbol = shoulder.getDatacenterBySymbol
getDatacenterById = shoulder.getDatacenterById
getGroupByPid = store_group.getByPid
getGroupByGroupname = store_group.getByGroupname
getGroupById = store_group.getById
getUserByPid = store_user.getByPid
getUserByUsername = store_user.getByUsername
getUserById = store_user.getById
getAdminUser = store_user.getAdminUser
getProfileByLabel = store_profile.getByLabel
getProfileById = store_profile.getById


def getIdentifier(identifier, prefixMatch=False):
    if prefixMatch:
        l = list(
            StoreIdentifier.objects.select_related(
                "owner", "owner__group", "ownergroup", "datacenter", "profile"
            ).filter(identifier__in=util.explodePrefixes(identifier))
        )
        if len(l) > 0:
            return max(l, key=lambda si: len(si.identifier))
        else:
            raise StoreIdentifier.DoesNotExist()
    else:
        return StoreIdentifier.objects.select_related(
            "owner", "owner__group", "ownergroup", "datacenter", "profile"
        ).get(identifier=identifier)
