from pathlib import Path
from tinkertool.scripts.create_ppe.config import BuildPPEConfig
from tinkertool.scripts.create_ppe.create_ppe import build_ppe

if __name__ == "__main__":
    build_ppe_config = BuildPPEConfig(
        simulation_setup_path='../aerosol_ppe_settings.ini',
        overwrite=True,
        build_base_only=False,
        log_dir                 = Path(__file__).parent.joinpath('../output_files', 'logs').resolve(),
        log_mode                = 'w',
        build_only=True
    )

    build_ppe(build_ppe_config)
