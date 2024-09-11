from ezid_client import EZIDClient as ezid_client

import argparse

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Use the EZID API client library ezid_client.py to test EZID.")

    parser.add_argument('-e', '--env', type=str, required=True, choices=['test', 'dev', 'stg', 'prd'], help='Environment')
    parser.add_argument('-u', '--username', type=str, required=False, help='user name')
    parser.add_argument('-p', '--password', type=str, required=False, help='password')
 
    args = parser.parse_args()
    env = args.env
    username = args.username
    password = args.password

    server_url = {
        'test': 'http://127.0.0.1:8000/',
        'dev': 'https://ezid-dev.cdlib.org/',
        'stg': 'https://ezid-stg.cdlib.org/',
        'prd': 'https://ezid.cdlib.org/'
    }

    client = ezid_client(server_url.get(env), username=username, password=password)

    print("view")
    ret = client.view("ark:/13030/m5z94194")
    print(ret)

    print("mint")
    ret = client.mint("ark:/99999/fk4")
    print(ret)

    print("status")
    ret = client.status()
    print(ret)

if __name__ == "__main__":
    main()


