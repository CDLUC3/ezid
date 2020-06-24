"""
Requires environment variables to be set for (KEY [DEFAULT]):
EZID_SERVER         ["http://localhost:8000/"]
EZID_USERNAME       ["admin"]
EZID_PASSWORD       ["admin"]

Optional:
EZID_TEST_SHOULDER  ["ark:/99999/fk4"]
EZID_TEST_ID        ["ark:/13030/c75t3g01g"]
"""
import os
from collections import namedtuple
import apicli_py2 as api
import pytest


def get_parameters():
    cfg = namedtuple("CFG", "server, username, password")
    cfg.server = os.environ.get("EZID_SERVER", "http://localhost:8000/")
    cfg.username = os.environ.get("EZID_USERNAME", "admin")
    cfg.password = os.environ.get("EZID_PASSWORD", "admin")
    return cfg


def test_login_logout():
    # Login and logout
    cfg = get_parameters()
    cli = api.EZIDClient(cfg.server, username=cfg.username, password=cfg.password)
    res = cli.login()
    assert res["status"] == "success"
    res = cli.logout()
    assert res["status"] == "success"


def test_login_fail():
    # Check for login failure
    cfg = get_parameters()
    cli = api.EZIDClient(
        cfg.server, username=cfg.username, password=cfg.password + "XXX"
    )
    res = ""
    res = cli.login()
    assert res["status"] == "error"
    assert res["status_message"] == "unauthorized"


@pytest.fixture
def ezid_connection():
    # Setup a fixture for repeated tests
    cfg = get_parameters()
    cli = api.EZIDClient(cfg.server, username=cfg.username, password=cfg.password)
    res = cli.login()
    assert res["status"] == "success"
    return cli


def test_status(ezid_connection):
    # Get service status
    res = ezid_connection.status()
    assert res["status"] == "success"


def test_logout(ezid_connection):
    res = ezid_connection.logout()
    assert res["status"] == "success"
    # TODO: logout when not logged in should probably return an error, but currently returns success
    # res = ezid_connection.logout()
    # assert(res.lower().startswith("error"))


def test_mint_identifier(ezid_connection):
    shoulder = os.environ.get("EZID_TEST_SHOULDER", "ark:/99999/fk4")
    pid_who = "testing mint_identifier"
    pid_when = "2020-06-24"
    pid_what = "test entry"
    params = ["erc.who", pid_who, "erc.when", pid_when, "erc.what", pid_what]
    res = ezid_connection.mint(shoulder, params=params)
    assert res["status"] == "success"
    pid = res["status_message"]
    res = ezid_connection.view(pid)
    assert res["status"] == "success"
    assert res["_owner"] == ezid_connection._username
    assert res["erc.who"] == pid_who
    assert res["erc.what"] == pid_what
    assert res["erc.when"] == pid_when


def test_view_identifier(ezid_connection):
    pid = os.environ.get("EZID_TEST_ID", "ark:/13030/c75t3g01g")
    res = ezid_connection.view(pid)
    assert res["status"] == "success"
