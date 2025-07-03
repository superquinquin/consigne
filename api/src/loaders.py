import re
import os
import yaml
from pathlib import Path
from yaml import SafeLoader
from collections import defaultdict
from abc import ABC, abstractmethod

from typing import Any, Type

Payload = dict[str, Any]
ESCAPED = ["\\" ,"^" ,"$" ,"." ,"|" ,"?" ,"*" ,"+" ,"(" ,")" ,"[" ,"]" ,"{" ,"}"]

class Loader(ABC):
    @abstractmethod
    def load(self, fp: str|Path) -> dict[str, Any]:
        raise NotImplementedError()

class YamlLoader(Loader):
    def load(self, fp: str|Path) -> dict[str, Any]:
        with open(fp, "r") as f:
            payload = yaml.load(f, SafeLoader)
        return payload

class Pattern(object):
    prefix: str
    suffix: str

    def __init__(self, prefix: str, suffix: str):
        self.prefix = prefix
        self.suffix = suffix
    
    @property
    def find(self) -> str:
        prefix, suffix = self._escaped()
        return f"^{prefix}.*?{suffix}$"

    @property
    def sub(self) -> str:
        prefix, suffix = self._escaped()
        return f"^{prefix}|{suffix}"

    def key(self, s: str) -> str:
        return re.sub(re.compile(self.sub), "", s).strip()

    def is_pattern(self, s: str) -> bool:
        return bool(re.search(re.compile(self.find), s))

    def _escaped(self) -> tuple[str, str]:
        prefix = "".join([c if c not in ESCAPED else f"\{c}" for c in self.prefix])
        suffix = "".join([c if c not in ESCAPED else f"\{c}" for c in self.suffix])
        return (prefix, suffix)

class ConfigLoader:
    def __init__(
        self, 
        d: dict[str, Any]=None, 
        environ_pattern: Pattern = Pattern("${", "}"), 
        template_pattern: Pattern = Pattern("{{", "}}"),
        allow_env_specific_merging: bool=False,
        main_configs_name: str= "app"
    ) -> None:
        self.environ_pattern = environ_pattern
        self.template_pattern = template_pattern
        self.allow_env_specific_merging = allow_env_specific_merging
        self.main_configs_name = main_configs_name
        self.d = {}
        if d is not None:
            self.d = d
    
    def load(
        self, 
        fp: str|Path,
        loader: Type[Loader] = YamlLoader, 
        template: dict[str, Any]|None=None, 
        overwrite: dict[str, Any]|None=None
    ) -> dict[str, Any]:
        payload = loader().load(fp)
        payload = self.map(payload, template, overwrite)
        return payload

    def map(
        self, 
        d: dict[str, Any], 
        template: dict[str, Any]|None=None, 
        overwrite: dict[str, Any]|None=None
    ) -> dict[str, Any]:
        if template is None:
            template = {}
        if overwrite is None:
            overwrite = {}
        self.d = d
        self.template = template
        self.overwrite = overwrite
        self.d = self._map(self.d, [])

        if self.allow_env_specific_merging:
            self._merge()
        else:
            self.d = self.d.get(self.main_configs_name)
        return self.d

    def _map(self, d: dict[str, Any], location: list[str]) -> dict[str, Any]:
        if location is None:
            location = []
        if d is None:
            raise ValueError("Mapper is missing base dict.")

        for k,v in d.items():
            d[k] = self._v_handler(k, v, location + [k])
        return d
        
    def _v_handler(self, key: str, value: Any, location: list[str]):
        layer = ".".join(location)
        if isinstance(value, str) and self.environ_pattern.is_pattern(value):
            value = self._get_environ_value(key, value)
        elif isinstance(value, str) and self.template_pattern.is_pattern(value):
            value = self._get_template_value(value)
        elif layer in self.overwrite.keys():
            value = self.overwrite.get(layer)
        elif isinstance(value, list):
            value = [self._v_handler(key, elm, location) for elm in value]
        elif isinstance(value, dict):
            value = self._map(value, location)
        return value

    def _get_environ_value(self, key: str, value: str) -> str:
        env = os.environ.get(self.environ_pattern.key(value), None)
        if env is None:
            raise KeyError(f"ENV variable {key} not found.")
        return env

    def _get_template_value(self, value: str) -> Any:
        return self.template.get(self.template_pattern.key(value), None)
        
    def _merge(self) -> dict[str, Any]:
        env = os.environ.get("ENV", None)
        main_config = self.d.get(self.main_configs_name, None)

        if main_config is None:
            raise KeyError(f"Main configuration dict `app` not found.")

        if env is None:
            env = main_config.get("env", None)

        if env is None:
            raise EnvironmentError(f"`ENV` environment variable is unset.")

        env_config = self.d.get(env, {})
        config = defaultdict(dict)
        for key in list(set(list(main_config.keys()) + list(env_config.keys()))):
            mcfg = main_config.get(key, None)
            ecfg = env_config.get(key, None)


            if mcfg is None and ecfg is None:
                continue

            elif not mcfg or not ecfg:
                config[key] = list(filter(None, [mcfg, ecfg]))[0]

            elif type(mcfg) != type(ecfg):
                raise TypeError(f"unmatching types for {key}.")
            elif isinstance(mcfg, dict) and isinstance(ecfg, dict):
                # -- env cfg must override in case of duplicates
                config[key] = {**mcfg, **ecfg}

            else:
                # -- last case, type is not dict, override with env config
                config[key] = ecfg
        return config
