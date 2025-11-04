from tinkertool.scripts.create_ppe.cli import (
    parse_create_ppe_cli_args,
    parse_build_ppe_cli_args,
    parse_submit_ppe_cli_args
)
from tinkertool.scripts.create_ppe.create_ppe import (
    create_ppe,
    build_ppe,
    check_build,
    prestage_ensemble,
    submit_ppe
)

def create_ppe_CLI():
    config = parse_create_ppe_cli_args()
    create_ppe(config)

def build_ppe_CLI():
    config = parse_build_ppe_cli_args()
    build_ppe(config)

def check_build_CLI():
    config = parse_submit_ppe_cli_args()
    check_build(config)

def prestage_ensemble_CLI():
    config = parse_submit_ppe_cli_args()
    prestage_ensemble(config)

def submit_ppe_CLI():
    config = parse_submit_ppe_cli_args()
    submit_ppe(config)

if __name__ == "__main__":
    create_ppe_CLI()
