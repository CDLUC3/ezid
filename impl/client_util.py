import requests
import base64
import re

import impl.anvl

def http_request(method, url, user_name, password, data):
    data = impl.anvl.format(data)
    # convert data to byte string
    try:
        data = data.encode('UTF-8')
    except:
        pass

    success = False
    status_code = -1
    text = ""
    err_msg = ""

    headers = {
        "Content-Type": "text/plain; charset=UTF-8",
        "Authorization": "Basic " + base64.b64encode(f"{user_name}:{password}".encode('utf-8')).decode('utf-8'),
    }
    try:
        if method.upper() == 'PUT':
            r = requests.put(url=url, headers=headers, data=data)
        else:
            r = requests.post(url=url, headers=headers, data=data)
        
        status_code = r.status_code
        text = r.text
        success = True
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
        err_msg = "HTTPError: " + str(e)[:200]
    return success, status_code, text, err_msg


def mint_identifer(base_url, user_name, password, shoulder, data):
    url = f'{base_url}/shoulder/{shoulder}'
    http_success, status_code, text, err_msg = http_request('post', url, user_name, password, data)
    
    id_created = None
    if http_success:
        # should return text as:
        # success: doi:10.15697/FK27S78 | ark:/c5697/fk27s78
        # success: ark:/99999/fk4m631r0h
        # error: bad request - no such shoulder created
        if text.strip().startswith("success"):
            list_1 = text.split(':', 1)
            if len(list_1) > 1:
                ids = list_1[1]
                list_2 = ids.split("|")
                if len(list_2) > 0:
                    id_created = list_2[0].strip()
        
    status = (shoulder, id_created, text)

    return status

def create_identifer(base_url, user_name, password, identifier, data):
    url = f'{base_url}/id/{identifier}'
    http_success, status_code, text, err_msg = http_request('put', url, user_name, password, data)
    
    id_created = None
    if http_success:
        # should return text as:
        # success: doi:10.5072/FK2TEST_1 | ark:/b5072/fk2test_1
        # success: ark:/99999/fk4test_1
        # error: bad request - identifier already exists
        if text.strip().startswith("success"):
            list_1 = text.split(':', 1)
            if len(list_1) > 1:
                ids = list_1[1]
                list_2 = ids.split("|")
                if len(list_2) > 0:
                    id_created = list_2[0].strip()
        
    status = (id_created, text)

    return status

def update_identifier(base_url, user_name, password, id, data):
    url = f"{base_url}/id/{id}"
    http_success, status_code, text, err_msg = http_request('post', url, user_name, password, data)
    if http_success and status_code == 200:
        print(f"ok update identifier - {id} updated with new data: {data}")
    else:
        print(f"ERROR update identifier - update {id} failed - status_code: {status_code}: {text}: {err_msg}")


def delete_identifier(base_url, user_name, password, id):
    url = f'{base_url}/id/{id}'
    success = False
    status_code = -1
    text = ""
    err_msg = ""

    headers = {
        "Content-Type": "text/plain; charset=UTF-8",
        "Authorization": "Basic " + base64.b64encode(f"{user_name}:{password}".encode('utf-8')).decode('utf-8'),
    }
    try:
        r = requests.delete(url=url, headers=headers)
        status_code = r.status_code
        text = r.text
        success = True
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
        err_msg = "HTTPError: " + str(e)[:200]
    
    if success and status_code == 200:
        print(f"ok delete identifier - {id} ")
    else:
        print(f"ERROR delete identifier - update {id} failed - status_code: {status_code}: {text}: {err_msg}")


