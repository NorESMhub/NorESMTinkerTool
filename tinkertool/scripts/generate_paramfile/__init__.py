# --- constants
PARAMFILE_INPUT_TYPES = ['user_nl', 'CTSM_param_file', 'FATES_param_file']

FORMAT_TO_FILE_METHOD = ['f-string', 'write-lines']

# make generate_paramfile available at package level
from tinkertool.scripts.generate_paramfile.generate_paramfile import generate_paramfile