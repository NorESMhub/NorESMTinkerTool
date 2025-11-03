import os
import re
import logging
import configparser

# get the logger - assuming this is run from create_ppe.build_ppe so that tinkertool_log is set up
logger = logging.getLogger('tinkertool_log')

def format_value(value: str) -> str:
    """
    Format a string for Fortran namelist: booleans and numerics are left as-is,
    comma-separated lists are handled, other strings are quoted.

    Parameters
    ----------
    value : str
        The string to format.
    """
    value = value.strip()
    # Handle Fortran logicals
    if value.lower() in ['.true.', '.false.']:
        return value.lower()
    # Handle single numeric value (int, float, E or D notation)
    if re.match(r'^-?\d+(\.\d*)?([eEdD][+-]?\d+)?$', value):
        return value
    # Handle comma-separated list of numbers or booleans
    if "," in value:
        vals = [v.strip() for v in value.split(",")]
        if all(re.match(r'^-?\d+(\.\d*)?([eEdD][+-]?\d+)?$', v) or v.lower() in ['.true.', '.false.'] for v in vals):
            return ", ".join(vals)
        # Otherwise, treat as strings
        return ", ".join(f"'{v}'" for v in vals)
    # Otherwise, treat as string
    return f"'{value}'"


def setup_usr_nlstring(
  user_nl_config: configparser.ConfigParser,
  component_name: str
) -> str:
  """
  Takes inn configparser objects of default namelist settings for setting dianoistics and control namelist settings.

  Parameters:
  -----------
  user_nl_config : configparser.ConfigParser
      A configparser object containing default namelist settings.
  component_name : str
      Name of the component for which the namelist settings are being set up, e.g. 'cam', 'clm', etc.
      Per now only 'blom' is the exception where the namelist section is not used.
  """
  user_nlstring = ""
  if 'misc' in user_nl_config.sections():
    for key in user_nl_config['misc']:
      user_nlstring += key + " = " + format_value(user_nl_config['misc'][key]) + "\n"
    user_nl_config.remove_section('misc')
  for section in user_nl_config.sections():
    if component_name.lower() != 'blom':
      user_nlstring += f"&{section}\n"
    for key in user_nl_config[section]:
      if key.startswith("fincl"):
        diag_list = user_nl_config[section][key].split("\n")
        user_nlstring += key + f" = '{diag_list[0]}',\n"
        for diag in diag_list[1:-1]:
          user_nlstring += f"         '{diag}',\n"
        user_nlstring +=  f"         '{diag_list[-1]}'\n"

      elif key.endswith("_specifier"):
        emis_specfier = user_nl_config[section][key].split("\n")
        user_nlstring += key + f" = '{emis_specfier[0]}',\n"
        for emis in emis_specfier[1:-1]:
          user_nlstring += f"                  '{emis}',\n"
        user_nlstring += f"                  '{emis_specfier[-1]}'\n"

      else:
        user_nlstring += key + " = " + format_value(user_nl_config[section][key]) + "\n"
    if component_name.lower() != 'blom':
      user_nlstring += "/\n"
    user_nlstring += "\n"
  return user_nlstring


def write_user_nl_file(
    caseroot:       str,
    usernlfile:     str,
    user_nl_str:    str
) -> None:
    """write user_nl string to file

    Parameters
    ----------
    caseroot : str
        root directory of the case
    usernlfile : str
        name of the user_nl file, e.g. user_nl_cam, user_nl_clm ...
    user_nl_str : str
        string to be written to the user_nl file
    verbose : bool
        verbose output
    """
    user_nl_file = os.path.join(caseroot, usernlfile)
    logger.info(f"...Writing to user_nl file: {usernlfile}")
    with open(user_nl_file, "a") as funl:
        funl.write(user_nl_str)