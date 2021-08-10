import datetime
import pathlib
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

import ezidapp.models.shoulder
import impl.nog.minter
import impl.util


def add_basic_auth_header(request, username, password):
    request["Authorization"] = impl.util.basic_auth(username, password)


def encode(s):
    if isinstance(s, str):
        s = s.encode('utf-8')
    return urllib.parse.quote(s, ":/")


def decode(s):
    return s.decode('utf-8')


def shoulder_to_dict(s):
    """Return a dict of the user defined values/attributes in a Shoulder
    model."""
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


def create_shoulder(
    namespace_str, organization_name='test shoulder', root_path=None, mask_str='eedk'
):
    is_doi = namespace_str[:4] == 'doi:'
    prefix_str, shoulder_str = namespace_str.split('/')[-2:]
    shoulder_model = ezidapp.models.shoulder.Shoulder.objects.create(
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
    impl.nog.minter.create_minter_database(namespace_str, root_path, mask_str)
    return shoulder_model


def add_shoulder_to_user(shoulder_model, user_model):
    user_model.shoulders.add(shoulder_model)


def check_response(resp):
    if resp.status_code != 200:
        with open('/tmp/test_error.html', 'wb') as f:
            f.write(resp.content)
        subprocess.call(['/usr/bin/chromium-browser', 'out.html'])


def dir_tree(path):
    if isinstance(path, str):
        path = pathlib.Path(path)
    return '\n'.join(p.as_posix() for p in path.rglob('*'))
