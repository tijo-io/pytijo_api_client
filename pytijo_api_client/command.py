import platform
import ntpath
import distutils.spawn
import os
import hashlib
from .utils import LRUCache

DEFAULT_CACHE_FOLDER = "~/.tijo"
DEFAULT_COMMAND_LRU_CAPACITY = 100
ALL_COMMAND_LRU = LRUCache(capacity=1000)
DEFAULT_FACTS = [
    "system",
    "kernel",
    "machine",
    "python_version",
    "command_path",
    "command_path_filesize",
]


class Command:
    def __init__(
        self,
        args,
        cache_folder=DEFAULT_CACHE_FOLDER,
        lru_capacity=DEFAULT_COMMAND_LRU_CAPACITY,
        template=None,
    ):
        if len(args) == 0 or args[0] is None or len(args[0]) == 0:
            raise AttributeError(
                "arguments must be a list of strings and should contain at least one value"
            )
        self.args = args
        self.template = template
        self.cache_folder = os.path.expanduser(cache_folder) if cache_folder else None
        self.lru_capacity = lru_capacity
        self.system = platform.system()
        self.kernel = platform.release()
        self.machine = platform.machine()
        self.python_version = platform.python_version()
        self.command = args[0]
        self.command_args = args[1:]
        self.command_basename = ntpath.basename(args[0])
        self.command_path = distutils.spawn.find_executable(args[0])
        self.command_path_filesize = 0
        try:
            self.command_path_filesize = (
                os.path.getsize(self.command_path)
                if self.command_path and os.path.exists(self.command_path)
                else 0
            )
        except TypeError:
            pass

        self.cache_key = hashlib.md5(" ".join(args[1:]).encode("utf-8")).hexdigest()

    def get_template(self, tijoapi, disable_cache=False):
        if not disable_cache and self.template:
            return self.template

        command_templates = ALL_COMMAND_LRU.get(self.command)
        if command_templates is None and self.cache_folder:
            command_templates = LRUCache(
                capacity=self.lru_capacity,
                file=os.path.join(self.cache_folder, self.command),
            )
            ALL_COMMAND_LRU.set(self.command, command_templates)

        self.template = command_templates.get(self.cache_key)

        if disable_cache or not self.template:
            # find themplate in tijo api
            self.template = tijoapi.search_template(
                basename=self.command_basename,
                args=self.command_args,
                facts=self._get_facts(),
            )
            if self.template:
                command_templates.set(self.cache_key, self.template)
                command_templates.save()
        return self.template

    def push_template(
        self, tijoapi, name=None, tags=None, facts=None, facts_attributes=None
    ):
        if tags is not None and isinstance(tags, list) and len(tags) > 0:
            tags = " ".join(tags)

        # calculate the facts
        default_facts = self._get_facts(facts_attributes)
        default_facts = {} if default_facts is None else default_facts
        if facts is not None and len(facts) > 0:
            for key in facts:
                default_facts[key] = facts[key]

        return tijoapi.post_template(
            basename=self.command_basename,
            name=name,
            template=self.template,
            tags=tags,
            facts=default_facts,
        )

    def _get_facts(self, attributes=DEFAULT_FACTS):
        if attributes is None or len(attributes) == 0:
            return None
        facts = {}
        for attribute in attributes:
            if hasattr(self, attribute) and getattr(self, attribute):
                facts[attribute] = getattr(self, attribute)
        return facts if len(facts) > 0 else None
