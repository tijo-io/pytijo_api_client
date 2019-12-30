import platform
import ntpath
import distutils.spawn
import os
import hashlib
import requests
import json
import logging
import time
from .utils import LRUCache

DEFAULT_TIJO_API = "http://api.tijo.io/v1"
DEFAULT_CACHE_FOLDER = "~/.tijo"
DEFAULT_TOKEN_FILE = ".token"
DEFAULT_COMMAND_LRU_CAPACITY = 100
ALL_COMMAND_LRU = LRUCache(capacity=1000)

DEFAULT_HEADERS = {"content-type": "application/json", "accept": "application/json"}

DEFAULT_FACTS = [
    "system",
    "kernel",
    "machine",
    "python_version",
    "command_path",
    "command_path_filesize",
]


class NotAuthenticated(Exception):
    pass


class TijoApi:
    def __init__(
        self,
        cache_folder=DEFAULT_CACHE_FOLDER,
        tijo_api=DEFAULT_TIJO_API,
        insecure=False,
        timeout=60,
    ):
        self.cache_folder = os.path.expanduser(cache_folder) if cache_folder else None
        self.token_file = os.path.join(self.cache_folder, DEFAULT_TOKEN_FILE)
        self.token = None
        self.refresh_token = None
        self.token_time = None
        self._load_token()
        self.tijo_api = tijo_api
        self.insecure = insecure
        self.timeout = timeout

    def login(self, email, password, saveToken=False):
        data = {"email": email, "password": password}
        logging.debug("login into {}".format("{}/auth/login".format(self.tijo_api)))
        resp = requests.post(
            "{}/auth/login".format(self.tijo_api),
            verify=not self.insecure,
            timeout=self.timeout,
            headers=DEFAULT_HEADERS,
            data=json.dumps(data),
        )
        if resp is None or (resp.status_code != 200 and resp.status_code != 201):
            return None
        try:
            data = json.loads(resp.content.decode("utf-8"))
            logging.debug("login result {}".format(data))
            if "token" in data and "expirationTime" in data and "refreshToken" in data:
                self.token = data["token"]
                self.refresh_token = data["refreshToken"]
                self.token_time = int(data["expirationTime"])
                if saveToken:
                    self._save_token()
            return data
        except ValueError:
            return None
        return None

    def register(self, email, password, firstName, lastName):
        data = {
            "email": email,
            "password": password,
            "firstName": firstName,
            "lastName": lastName,
        }
        resp = requests.post(
            "{}/auth/register".format(self.tijo_api),
            verify=not self.insecure,
            timeout=self.timeout,
            headers=DEFAULT_HEADERS,
            data=json.dumps(data),
        )
        if resp is None or (resp.status_code != 200 and resp.status_code != 201):
            return None
        return True

    def resend(self, email, password):
        data = {"email": email, "password": password}
        resp = requests.post(
            "{}/auth/resend".format(self.tijo_api),
            verify=not self.insecure,
            timeout=self.timeout,
            headers=DEFAULT_HEADERS,
            data=json.dumps(data),
        )
        if resp is None or (resp.status_code != 200 and resp.status_code != 201):
            return None
        return True

    def reset(self, email):
        data = {"email": email}
        resp = requests.post(
            "{}/auth/reset".format(self.tijo_api),
            verify=not self.insecure,
            timeout=self.timeout,
            headers=DEFAULT_HEADERS,
            data=json.dumps(data),
        )
        if resp is None or (resp.status_code != 200 and resp.status_code != 201):
            return None
        return True

    def post_template(self, basename, name, template, tags=None, facts=None):
        data = {
            "command": basename,
            "name": name if name is not None else basename,
            "json": template,
        }
        if tags is not None and isinstance(tags, list) and len(tags) > 0:
            data["tags"] = " ".join(tags)
        elif tags is not None:
            data["tags"] = tags

        if facts is not None and len(facts) > 0:
            data["command_facts"] = facts

        headers = DEFAULT_HEADERS.copy()
        headers["Authorization"] = "Bearer {}".format(self._get_token())
        resp = requests.post(
            "{}/templates".format(self.tijo_api),
            verify=not self.insecure,
            timeout=self.timeout,
            headers=headers,
            data=json.dumps(data),
        )
        logging.debug(
            "post template result code={} content={}".format(
                resp.status_code, resp.content
            )
        )
        if resp is None or (resp.status_code != 200 and resp.status_code != 201):
            return None
        try:
            return json.loads(resp.content.decode("utf-8"))
        except ValueError:
            return None
        return None

    def search_templates(self, basename, args=None, facts=None, offset=0, limit=1):
        data = {"command": basename}
        if facts is not None and len(facts) > 0:
            data["command_facts"] = facts
        if args and len(args) > 0:
            data["command_args"] = " ".join(args)

        resp = requests.post(
            "{}/templates/search?offset={}&limit={}".format(
                self.tijo_api, offset, limit
            ),
            verify=not self.insecure,
            timeout=self.timeout,
            headers=DEFAULT_HEADERS,
            data=json.dumps(data),
        )

        if resp is None or (resp.status_code != 200 and resp.status_code != 201):
            return None
        try:
            data = json.loads(resp.content.decode("utf-8"))
            if (
                data
                and "templates" in data
                and data["templates"]
                and len(data["templates"]) > 0
            ):
                return data["templates"]
        except ValueError:
            return None
        return None

    def search_template(self, basename, args=None, facts=None, offset=0, limit=1):
        templates = self.search_templates(
            basename=basename, args=args, facts=facts, offset=offset, limit=limit
        )
        if templates and len(templates) > 0 and "json" in templates[0]:
            return templates[0]["json"]

    def _get_token(self):
        if self.token and self.token_time > int(time.time() * 1000):
            return self.token
        raise NotAuthenticated(("token expired" if self.token else "not authenticated"))

    def _save_token(self):
        logging.debug("saving token into {}".format(self.token_file))
        dir = os.path.dirname(self.token_file)
        if not os.path.exists(dir):
            os.makedirs(dir)
        with open(self.token_file, "w") as outfile:
            json.dump(
                {
                    "token": self.token,
                    "refreshToken": self.refresh_token,
                    "time": self.token_time,
                },
                outfile,
                indent=4,
            )

    def _load_token(self):
        if not self.token and os.path.exists(self.token_file):
            logging.debug("loading token from {}".format(self.token_file))
            with open(self.token_file, "r") as f:
                data = json.load(f)
                if "token" in data and "time" in data and "refreshToken" in data:
                    self.token = data["token"]
                    self.token_time = data["time"]
                    self.refresh_token = data["refreshToken"]
                    logging.debug("loaded token {}".format(data["token"]))
