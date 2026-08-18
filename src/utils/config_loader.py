import yaml
import os
from typing import Dict, Any


class ConfigLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = None
        return cls._instance

    def load(self, config_path: str = None) -> Dict[str, Any]:
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "config",
                "config.yaml"
            )

        with open(config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

        os.makedirs(self._config["output"]["report_dir"], exist_ok=True)

        return self._config

    def get(self, key: str, default=None) -> Any:
        if self._config is None:
            self.load()
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    @property
    def config(self) -> Dict[str, Any]:
        if self._config is None:
            self.load()
        return self._config
