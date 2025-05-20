import copy
import configparser
from typing import Union
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
        config.read_file(f)

    config.input_file = config_file
    return copy.copy(config)