import sys
import traceback
from pathlib import Path

def add_CIME_paths(
    cesmroot: str | Path
) -> None:
    """Add CIME paths to the system path.

    Parameters
    ----------
    cesmroot : str | Path
        Path to the CESM root directory.
    """
    cime_path = Path(cesmroot).joinpath("cime").resolve()

    if not cime_path.is_dir():
        raise FileNotFoundError(f"CIME directory not found: {cime_path}")

    sys.path.insert(0, str(cime_path))

def add_CIME_paths_and_import(
    cesmroot: str | Path
) -> None:
    """Add CIME paths to the system path and import necessary functions to build and clone cases.

    Parameters
    ----------
    cesmroot : str
        Path to the CESM root directory.
    """
    cesmroot = Path(cesmroot).resolve()
    add_CIME_paths(cesmroot)
    try:
        from tinkertool.setup.case import build_base_case, clone_base_case
        # Make functions available at module level
        globals()['build_base_case'] = build_base_case
        globals()['clone_base_case'] = clone_base_case
    except ImportError:
        traceback.print_stack()
        err_msg = f"ERROR: CIME not found in {cesmroot}, update CESMROOT environment variable"
        print(err_msg)