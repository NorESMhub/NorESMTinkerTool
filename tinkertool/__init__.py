from pathlib import Path
NorESMTinkerTool_abspath = Path(__file__).parent.resolve()

VALID_COMPONENTS = ['cam', 'cice', 'clm', 'blom']

# --- Patch logging to add info_detailed method
from tinkertool.utils.custom_logging import patch_info_detailed
patch_info_detailed()


