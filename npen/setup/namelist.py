def setup_usr_nlstring(control_default, control_user=None):
  """
  Takes inn configparser objects of default namelist settings for setting dianoistics and control namelist settings.
  
  Parameters:
  -----------
  diagnostics_default : configparser object
    Default namelist settings for diagnostics.Read in from config/diagnostics_default.ini
  control_default : configparser object
    Default namelist settings for  in from config/control_default.ini  
  control_user : configparser object
    User namelist settings for control namelist
  """
  user_nlstring = ""

  for section in control_default.sections():
    if section != "DEFAULT":
      user_nlstring += f" &{section}\n"
    for key in control_default[section]:
      if key.startswith("fincl"):
        diag_list = control_default[section][key].split("\n")
        user_nlstring += "   " + key + f" = '{diag_list[0]}'\n"
        for diag in diag_list[1:]:
          user_nlstring += f"         '{diag}'\n" 
      else:
        user_nlstring += "   " + key + " = " + control_default[section][key] + "\n"
    if section != "DEFAULT":
      user_nlstring += " /\n"
      user_nlstring += "\n"

  return user_nlstring
