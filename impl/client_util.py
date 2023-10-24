import requests
import base64
import re

import impl.anvl

def post_data(url, user_name, password, data):
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
        r = requests.post(url=url, headers=headers, data=data)
        status_code = r.status_code
        text = r.text
        success = True
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
        err_msg = "HTTPError: " + str(e)[:200]
    return success, status_code, text, err_msg


def mint_identifers(base_url, user_name, password, shoulder, data):
    url = f'{base_url}/shoulder/{shoulder}'
    http_success, status_code, text, err_msg = post_data(url, user_name, password, data)
    
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

def update_identifier(base_url, user_name, password, id, data):
    url = f"{base_url}/id/{id}"
    http_success, status_code, text, err_msg = post_data(url, user_name, password, data)
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


