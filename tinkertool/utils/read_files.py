import copy
import configparser
from typing import Any, Union
from pathlib import Path

def read_config(
    config_file: Union[str, Path]
) -> configparser.ConfigParser:
    """Read a .ini config file and return a ConfigParser object.

    Parameters
    ----------
    config_file : str, Path
        Absolute path to the config file to be read. The config file should be in the .ini format [1].

    Returns
    -------
    configparser.ConfigParser
        A ConfigParser object containing the configuration parameters.
        To access the parameters, use the `config.get(section, option)` method,
        where `section` is the name of the section in the config file and `option`
        is the name of the option within that section.
    """

    config_file = Path(config_file).resolve()
    with open(config_file) as f:
        config = configparser.ConfigParser()
        config.optionxform = str # Preserve case sensitivity of option names
        config.read_file(f)

    config.input_file = config_file
    return copy.copy(config)

def safe_get_param_value(
    config_section,
    option: str,
    fallback=None
) -> Any:
    """Get a parameter value from config,
    converting 'nan', 'none', 'null', '' strings to None or fallback.

    Parameters
    ----------
    config_section : configparser.SectionProxy
        The config section to read from
    option : str
        The option name to get
    fallback : any, optional
        Value to return if option doesn't exist or is nan/none/null/empty string, by default None

    Returns
    -------
    Any
        The parameter value, or None if it was a nan/none/null/empty string
    """
    try:
        # If the option is absent, config_section.get should return fallback.
        # Use get with fallback=None to detect "missing" vs "present-but-empty".
        raw = config_section.get(option, fallback=None)

        # If option is missing, return the caller's fallback unchanged.
        if raw is None:
            return fallback

        # If value is a string sentinel meaning "no value", return None.
        if isinstance(raw, str):
            if raw.strip() == "" or raw.strip().lower() in ("nan", "none", "null"):
                return fallback

        # Otherwise return the raw (present) value.
        return raw
    except (configparser.NoOptionError, configparser.NoSectionError):
        return fallback
