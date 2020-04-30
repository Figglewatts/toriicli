from dataclasses import dataclass
import logging
import logging.config
import os
from os import path
import pkg_resources
from typing import Optional

from marshmallow import Schema, fields, post_load, ValidationError
import yaml

EXAMPLE_CONFIG_FILE = "example_config.yml"
CONFIG_NAME = "toriiproject.yml"


class ToriiCliConfigSchema(Schema):
    """Marshmallow schema for app config."""
    unity_executable_path = fields.Str(required=False, missing=None)
    unity_preferred_version = fields.Str(required=False, missing=None)

    @post_load
    def make_torii_cli_config(self, data, **kwargs):
        return ToriiCliConfig(**data)


CONFIG_SCHEMA = ToriiCliConfigSchema()


@dataclass
class ToriiCliConfig:
    """The config of the app. For details on each field, please see
    example_config.yml in the package."""
    unity_executable_path: str
    unity_preferred_version: str


def create_config(config_path: Optional[str]) -> str:
    """Create a config in a given path, or the CWD if none is given.
    Returns the path to the created config."""
    if config_path is None:
        config_path = os.getcwd()

    os.makedirs(config_path, exist_ok=True)

    # write the example config file to the config location
    out_file_path = path.join(config_path, CONFIG_NAME)
    with open(out_file_path, 'w') as config_file:
        # replace any funky windows line endings that might be in there
        example_cfg = pkg_resources.resource_string(
            "toriicli", EXAMPLE_CONFIG_FILE).decode("utf-8").replace("\r", "")
        config_file.write(example_cfg)

    return out_file_path


class ErrorFilter:
    """Filter error logs out of log statements."""
    def filter(self, record):
        return record.levelno < logging.ERROR


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("toriicli")
    logging.config.dictConfig({
        "version": 1,
        "formatters": {
            "standard": {
                "format": "%(message)s"
            },
            "error": {
                "format": "ERROR: %(message)s"
            }
        },
        "handlers": {
            "standard": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": "INFO",
                "stream": "ext://sys.stdout",
                "filters": ["no_errors"]
            },
            "error": {
                "class": "logging.StreamHandler",
                "formatter": "error",
                "level": "ERROR",
                "stream": "ext://sys.stderr"
            }
        },
        "filters": {
            "no_errors": {
                "()": ErrorFilter
            }
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["standard", "error"]
        }
    })
    return logger


def from_yaml(config_path: str) -> Optional[ToriiCliConfig]:
    """Load config file from given path.

    If an error occurred, it will print it and return None.
    """
    try:
        with open(config_path, 'r') as config_file:
            raw_config = yaml.safe_load(config_file)

            # handle the case of an empty config file
            if raw_config is None:
                raw_config = {}

            loaded_config = CONFIG_SCHEMA.load(raw_config)
            return loaded_config
    except OSError as err:
        # if there was an error opening the file
        logging.critical("Error opening config file: " + str(err))
        return None
    except yaml.YAMLError as err:
        # if the YAML was invalid
        logging.critical("Error in config file: " + str(err))
        return None
    except ValidationError as err:
        # if the schema says it's invalid
        _print_validation_err(err, config_path)
        return None


def _print_validation_err(err: ValidationError, name: str) -> None:
    """Internal function used for printing a validation error in the Schema.

    Args:
        err (ValidationError): The error to log.
        name (str): A human-readable identifier for the Schema data source. 
            Like a filename.
    """
    # build up a string for each error
    log_str = []
    log_str.append(f"Error validating config '{name}':")
    for field_name, err_msgs in err.messages.items():
        log_str.append(f"{field_name}: {err_msgs}")

    # print the joined up string
    logging.critical(" ".join(log_str))