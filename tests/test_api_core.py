import os
import pytest
from pytijo_api_client.command import ALL_COMMAND_LRU, Command
import pytijo_api_client
import hashlib
import responses
import json

CAPACITY = 2
CACHE_FOLDER = ".tmp/.tijo"
TIJO_API = "http://localhost:3000/api/v1"


def _delete_cache_file(cache_folder, command):
    file = os.path.join(os.path.expanduser(cache_folder), command)
    if os.path.exists(file):
        os.remove(file)


def _get_md5(args):
    return hashlib.md5(" ".join(args[1:]).encode("utf-8")).hexdigest()


@responses.activate
def test_lru_command(monkeypatch):
    def request_callback(request):
        payload = json.loads(request.body)
        resp_body = {
            "has_more": False,
            "templates": [
                {
                    "id": "419cf860-de6c-58c1-b04d-d24e72e8be93",
                    "created_at": 1560963283999,
                    "username": "tijo",
                    "author": "tijo Co.",
                    "command": "ifconfig",
                    "name": "ifconfig-interfaces",
                    "version": "0.0.1",
                    "version_major": 0,
                    "version_minor": 0,
                    "version_patch": 1,
                    "json": {
                        "interfaces": [
                            {
                                "id": "^([a-z]+\\d{1,2}):",
                                "ipv4_address": "inet (\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})",
                                "ipv6_address": "inet6 ((([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])))",
                                "mac_address": "ether ([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})",
                                "mtu": "mtu ([0-9]+)",
                                "status": "status: (\\w+)",
                            }
                        ]
                    },
                }
            ],
        }

        headers = {"content-type": "application/json"}
        return (200, headers, json.dumps(resp_body))

    responses.add_callback(
        responses.POST,
        "http://localhost:3000/api/v1/templates/search",
        callback=request_callback,
        content_type="application/json",
    )

    ALL_COMMAND_LRU.capacity = 2

    _delete_cache_file(CACHE_FOLDER, "ifconfig")
    _delete_cache_file(CACHE_FOLDER, "ip")
    _delete_cache_file(CACHE_FOLDER, "netstat")

    ifconfig = Command(["ifconfig"], CACHE_FOLDER, CAPACITY, TIJO_API)
    ifconfig_a = Command(["ifconfig", "-a"], CACHE_FOLDER, CAPACITY, TIJO_API)
    ifconfig_eth0 = Command(["ifconfig", "eth0"], CACHE_FOLDER, CAPACITY, TIJO_API)
    ip = Command(["ip", "-a"], CACHE_FOLDER, CAPACITY, TIJO_API)
    netstat = Command(["netstat"], CACHE_FOLDER, CAPACITY, TIJO_API)

    ifconfig.get_template()
    assert len(ALL_COMMAND_LRU.cache) == 1
    assert "ifconfig" in ALL_COMMAND_LRU.cache
    assert len(ALL_COMMAND_LRU.cache["ifconfig"].cache) == 1
    assert _get_md5(ifconfig.args) in ALL_COMMAND_LRU.cache["ifconfig"].cache

    ifconfig_a.get_template()
    assert len(ALL_COMMAND_LRU.cache) == 1
    assert "ifconfig" in ALL_COMMAND_LRU.cache
    assert len(ALL_COMMAND_LRU.cache["ifconfig"].cache) == 2
    assert _get_md5(ifconfig.args) in ALL_COMMAND_LRU.cache["ifconfig"].cache
    assert _get_md5(ifconfig_a.args) in ALL_COMMAND_LRU.cache["ifconfig"].cache

    ifconfig_eth0.get_template()
    assert len(ALL_COMMAND_LRU.cache) == 1
    assert "ifconfig" in ALL_COMMAND_LRU.cache
    assert len(ALL_COMMAND_LRU.cache["ifconfig"].cache) == 2
    assert _get_md5(ifconfig.args) not in ALL_COMMAND_LRU.cache["ifconfig"].cache
    assert _get_md5(ifconfig_a.args) in ALL_COMMAND_LRU.cache["ifconfig"].cache
    assert _get_md5(ifconfig_eth0.args) in ALL_COMMAND_LRU.cache["ifconfig"].cache

    ip.get_template()
    assert len(ALL_COMMAND_LRU.cache) == 2
    assert "ifconfig" in ALL_COMMAND_LRU.cache
    assert "ip" in ALL_COMMAND_LRU.cache

    netstat.get_template()
    assert len(ALL_COMMAND_LRU.cache) == 2
    assert "ifconfig" not in ALL_COMMAND_LRU.cache
    assert "ip" in ALL_COMMAND_LRU.cache
    assert "netstat" in ALL_COMMAND_LRU.cache

    ifconfig = Command(["ifconfig"], CACHE_FOLDER, CAPACITY, TIJO_API)
    ifconfig.get_template()
    assert "ifconfig" in ALL_COMMAND_LRU.cache
    assert len(ALL_COMMAND_LRU.cache["ifconfig"].cache) == 2
    assert _get_md5(ifconfig.args) in ALL_COMMAND_LRU.cache["ifconfig"].cache
    assert _get_md5(ifconfig_a.args) not in ALL_COMMAND_LRU.cache["ifconfig"].cache
    assert _get_md5(ifconfig_eth0.args) in ALL_COMMAND_LRU.cache["ifconfig"].cache
