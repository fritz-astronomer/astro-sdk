from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = "config"
CONFIG_FILENAME = "configuration.yml"

DEFAULT_ENVIRONMENT = "default"
DEFAULT_AIRFLOW_HOME = f"./.airflow/{DEFAULT_ENVIRONMENT}"
DEFAULT_DAGS_FOLDER = "./.airflow/.dags"


@dataclass
class Config:
    """
    SQL CLI Project configuration class to support reading and writing to configuration file.
    """

    project_dir: Path
    environment: str
    connections: list[dict[str, Any]] | None = None
    airflow_home: str | None = None
    airflow_dags_folder: str | None = None

    def get_filepath(self) -> Path:
        """
        Return configuration.yaml filepath.

        :returns: The path to the desired YAML configuration file
        """
        return self.project_dir / CONFIG_DIR / self.environment / CONFIG_FILENAME

    def from_yaml_to_dict(self) -> dict[str, Any]:
        """
        Return a dict with the content of the configuration.yaml.

        :returns: Content of the YAML configuration file as a python dictionary.
        """
        filepath = self.get_filepath()
        with open(filepath) as fp:
            yaml_with_env = os.path.expandvars(fp.read())
            yaml_config = yaml.safe_load(yaml_with_env)
        return yaml_config

    def from_yaml_to_config(self) -> Config:
        """
        Return a Config instance with the content of the configuration.yaml.

        :returns: Contents of the YAML configuration file.
        """
        yaml_config = self.from_yaml_to_dict()
        return Config(
            project_dir=self.project_dir,
            environment=self.environment,
            airflow_home=yaml_config.get("airflow", {}).get("home", DEFAULT_AIRFLOW_HOME),
            airflow_dags_folder=yaml_config.get("airflow", {}).get("dags_folder", DEFAULT_DAGS_FOLDER),
            connections=yaml_config["connections"],
        )

    def write_value_to_yaml(self, section: str, key: str, value: str) -> None:
        """
        Write a particular key/value to the desired configuration.yaml.

        Example:
        ```
            [section]
            key = value
        ```

        :param section: Section within the YAML file where the key/value will be recorded
        :param key: Key within the YAML file associated to the value to be recorded.
        :param value: Value associated to the key in the YAML file.
        """
        yaml_config = self.from_yaml_to_dict()
        yaml_config.setdefault(section, {})
        yaml_config[section][key] = value

        filepath = self.get_filepath()
        with open(filepath, "w") as fp:
            yaml.dump(yaml_config, fp)