from tinkertool.scripts.create_ppe.config import (
    CreatePPEConfig,
    BuildPPEConfig,
    SubmitPPEConfig
)
from tinkertool.scripts.create_ppe.create_ppe import (
    create_ppe,
    build_ppe,
    check_build,
    prestage_ensemble,
    submit_ppe
)

def create_ppe_CLI():
    config = CreatePPEConfig.from_cli() # type: ignore
    create_ppe(config)

def build_ppe_CLI():
    config = BuildPPEConfig.from_cli() # type: ignore
    build_ppe(config)

def check_build_CLI():
    config = SubmitPPEConfig.from_cli() # type: ignore
    check_build(config)

def prestage_ensemble_CLI():
    config = SubmitPPEConfig.from_cli() # type: ignore
    prestage_ensemble(config)

def submit_ppe_CLI():
    config = SubmitPPEConfig.from_cli() # type: ignore
    submit_ppe(config)

if __name__ == "__main__":
    create_ppe_CLI()
