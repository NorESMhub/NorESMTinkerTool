import os
import sys

def add_CIME_paths_and_import(
    cesmroot: str
) -> None:
    """Add CIME paths to the system path and import necessary functions to build and clone cases.

    Parameters
    ----------
    cesmroot : str
        Path to the CESM root directory.
    """
    _LIBDIR = os.path.join(cesmroot,"cime","scripts","Tools")
    sys.path.append(_LIBDIR)
    _LIBDIR = os.path.join(cesmroot,"cime","scripts","lib")
    sys.path.append(_LIBDIR)
    try:
        from tinkertool.setup.case import build_base_case, clone_base_case
    except ImportError:
        print(f"ERROR: CIME not found in {cesmroot}, update CESMROOT environment variable or set --cesm-root")

    global build_base_case, clone_base_case