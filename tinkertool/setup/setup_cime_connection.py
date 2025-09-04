import os
import sys
import traceback
from pathlib import Path

def add_CIME_paths(
    cesmroot: str
) -> None:
    """Add CIME paths to the system path.

    Parameters
    ----------
    cesmroot : str
        Path to the CESM root directory.
    """
    cime_path = Path(cesmroot).joinpath("cime").resolve()

    if not cime_path.is_dir():
        raise FileNotFoundError(f"CIME directory not found: {cime_path}")

    sys.path.insert(0, str(cime_path))

def add_CIME_paths_and_import(
    cesmroot: str
) -> None:
    """Add CIME paths to the system path and import necessary functions to build and clone cases.

    Parameters
    ----------
    cesmroot : str
        Path to the CESM root directory.
    """
    add_CIME_paths(cesmroot)
    try:
        from tinkertool.setup.case import build_base_case, clone_base_case
    except ImportError:
        traceback.print_stack()
        print(f"ERROR: CIME not found in {cesmroot}, update CESMROOT environment variable")

    global build_base_case, clone_base_case