from pathlib import Path
from tinkertool.scripts.create_ppe.config import BuildPPEConfig
from tinkertool.scripts.create_ppe.create_ppe import build_ppe

if __name__ == "__main__":
    build_ppe_config = BuildPPEConfig(
        simulation_setup_path='/cluster/projects/nn2345k/ovewh/NorESMTinkerTool/usermods/aerosol_ppe/aerosol_ppe_settings.ini',
        overwrite_base_case=False,
        overwrite_ppe=True,
        build_base_only=False,
        log_dir                 = Path('/cluster/projects/nn2345k/ovewh/NorESMTinkerTool/usermods/aerosol_ppe/').parent.joinpath('output_files', 'logs').resolve(),
        log_mode                = 'w',
        build_only=True,
        frozen_base_case=True,
        keepexe=True,
        verbose=2
    )

    build_ppe(build_ppe_config)
