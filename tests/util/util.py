import datetime
import subprocess
import urllib

import pathlib2

import ezidapp.models
import nog.bdb
import nog.minter


def add_basic_auth_header(request, username, password):
    request["Authorization"] = "Basic {} ".format(
        base64.b64encode(username + ":" + password)
    )


def encode(s):
    return urllib.quote(s, ":/")


def decode(s):
    return s.decode('utf-8')


def shoulder_to_dict(s):
    """Return a dict of the user defined values/attributes in a Shoulder model"""
    return {
        'active': s.active,
        'crossrefEnabled': s.crossrefEnabled,
        'datacenter': s.datacenter,
        'date': s.date,
        'isArk': s.isArk,
        'isCrossref': s.isCrossref,
        'isDatacite': s.isDatacite,
        'isDoi': s.isDoi,
        'isSupershoulder': s.isSupershoulder,
        'isTest': s.isTest,
        'isUuid': s.isUuid,
        'manager': s.manager,
        'minter': s.minter,
        'name': s.name,
        'prefix': s.prefix,
        'prefix_shares_datacenter': s.prefix_shares_datacenter,
        'registration_agency': s.registration_agency,
        'shoulder_type': s.shoulder_type,
        'storegroup_set': s.storegroup_set,
        'storeuser_set': s.storeuser_set,
        'type': s.type,
    }


def create_shoulder(namespace_str, organization_name='test shoulder', root_path=None):
    is_doi = namespace_str[:4] == 'doi:'
    prefix_str, shoulder_str = namespace_str.split('/')[-2:]
    ezidapp.models.Shoulder.objects.create(
        prefix=namespace_str,
        type='DOI' if is_doi else 'ARK',
        name=organization_name,
        minter="ezid:/{}".format('/'.join([prefix_str, shoulder_str])),
        datacenter=None,
        crossrefEnabled=is_doi,
        isTest=True,
        isSupershoulder=not shoulder_str,
        prefix_shares_datacenter=False,
        date=datetime.date.today(),
        active=True,
        manager='ezid',
    )
    impl.nog_minter.create_minter_database(
        prefix_str, shoulder_str, root_path=root_path
    )
    ezidapp.models.shoulder.loadConfig()


def check_response(resp):
    if resp.status_code != 200:
        with open('/tmp/test_error.html', 'wb') as f:
            f.write(resp.content)
        subprocess.call(['/usr/bin/chromium-browser', 'out.html'])


def dir_tree(path):
    if isinstance(path, str):
        path = pathlib2.Path(path)
    return '\n'.join(p.as_posix() for p in path.rglob('*'))
