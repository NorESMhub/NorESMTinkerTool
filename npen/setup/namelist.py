import configparser

def format_value(value: str) -> bool:
    """
    Check if the given string can be evaluated as an integer or a boolean.
    """
    if value.lower() in ['.true.', '.false.']:
      return value.lower()
    elif value.isnumeric():    
      return value
    elif value.replace(",","").isnumeric():
      return value
    elif value.split(",")[0].isnumeric():
      return value
    elif isinstance(value.split(","), list):
      string = ""
      for val in value.split(",")[:-1]:
        string += f"'{val}',"
      string += f"'{value.split(',')[-1]}'"
      return string
    else:
      return f"'{value}'"


def setup_usr_nlstring(user_nl_config: configparser.ConfigParser) -> None:
  """
  Takes inn configparser objects of default namelist settings for setting dianoistics and control namelist settings.
  
  Parameters:
  -----------
  user_nl_config : configparser.ConfigParser
      A configparser object containing default namelist settings.
  """
  user_nlstring = ""
  if 'misc' in user_nl_config.sections():
    for key in user_nl_config['misc']:
      user_nlstring += key + " = " + format_value(user_nl_config['misc'][key]) + "\n"
    user_nl_config.remove_section('misc')
  for section in user_nl_config.sections():
    user_nlstring += f"&{section}\n"
    for key in user_nl_config[section]:
      if key.startswith("fincl"):
        diag_list = user_nl_config[section][key].split("\n")
        user_nlstring += key + f" = '{diag_list[0]}',\n"
        for diag in diag_list[1:-1]:
          user_nlstring += f"         '{diag}',\n" 
        user_nlstring +=  f"         '{diag_list[-1]}'\n"  
      else:
        user_nlstring += key + " = " + format_value(user_nl_config[section][key]) + "\n"
    user_nlstring += "/\n"
    user_nlstring += "\n"
  return user_nlstring
