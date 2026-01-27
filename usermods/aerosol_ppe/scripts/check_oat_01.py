import sys
from pathlib import Path
from tinkertool.scripts.create_ppe.config import CheckBuildConfig
from tinkertool.scripts.create_ppe.create_ppe import check_build
import os

script_dir = Path(__file__).parent
cases_dir = os.getenv('PPE_SIMULATION_DIR')

# collect all paths
cases = []
cases_dir = Path(cases_dir)
for case in cases_dir.iterdir():
    if case.is_dir():
        if 'ensemble_member' in case.name or 'base_case_johannes_test' in case.name:
            cases.append(case)

# sort cases by name
cases.sort(key=lambda x: x.name)
print(cases)
check_build_config = CheckBuildConfig(
    cases       = cases,
    verbose     = 2,
    log_dir     = script_dir.joinpath('../output_files', 'logs').resolve(),
    log_mode    = 'w'
)

print(check_build_config)
if check_build(check_build_config):
    print("All cases are built correctly.")
else:
    print("Some cases are not built correctly. Please check the log file for details.")
    sys.exit(1)