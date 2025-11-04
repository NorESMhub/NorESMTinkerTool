# --- Patch logging to add info_detailed method
from tinkertool.utils.custom_logging import patch_info_detailed
patch_info_detailed()

# --- constants
PARAMFILE_INPUT_TYPES = ['user_nl', 'CTSM_param_file', 'FATES_param_file']