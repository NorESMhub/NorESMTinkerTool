import logging
import xarray as xr

from pathlib import Path
from collections import abc

from tinkertool.utils.check_arguments import validate_file

def _check_keyword_in_file(
    file_path: str | Path,
    keyword: str
) -> bool:
    """Check if a specific keyword exists in a given file.

    Parameters
    ----------
    file_path : str | Path
        The path to the file to be checked.
    keyword : str
        The keyword to search for in the file.

    Returns
    -------
    bool
        True if the keyword is found in the file, False otherwise.
    """
    with open(file_path, "r") as f:
        for line in f:
            if keyword in line:
                return True
    return False

def check_if_ctsm_param_is_perturbed(
    param_ranges_inpath: str | Path
) -> bool:
    """Check if any CTSM parameters are perturbed in the parameter ranges file.

    Parameters
    ----------
    param_ranges_inpath : str | Path
        The path to the parameter ranges file.

    Returns
    -------
    bool
        True if any CTSM parameters are perturbed, False otherwise.
    """
    ctsm_param_flag = "CTSM_param_file"
    return _check_keyword_in_file(param_ranges_inpath, ctsm_param_flag)

def check_if_fates_param_is_perturbed(
    param_ranges_inpath: str | Path
) -> bool:
    """Check if any FATES parameters are perturbed in the parameter ranges file.

    Parameters
    ----------
    param_ranges_inpath : str | Path
        The path to the parameter ranges file.

    Returns
    -------
    bool
        True if any FATES parameters are perturbed, False otherwise.
    """
    fates_param_flag = "FATES_param_file"
    return _check_keyword_in_file(param_ranges_inpath, fates_param_flag)

def make_new_ctsm_pamfile(
    pam_change_dict:    dict,
    orig_pamfile:       str | Path,
    file_dump:          str | Path = "ctsm_pamfile.nc"
) -> Path:
    """Make a new ctsm pamfile for the PPE, by changing parameters as specified in pam_change_dict.

    Parameters
    ----------
    pam_change_dict : dict
        Dictionary with parameter names as keys and new values or scaling
        factors as values. The pam_change_dict has parameter should have
        name of parameter to change as key, and change value as value.
        For scalar parameters this is assumed to be the new value of
        the parameter. For vector parameters the value is assumed to
        be a scaling value to scale the value in the original file with
    orig_pamfile : str or Path
        Path to the original CTSM parameter file to be modified.
    file_dump : str or Path, optional
        Path to save the new CTSM parameter file, by default "ctsm_pamfile.nc".
    """
    if not Path(orig_pamfile).exists():
        logging.error(f"Original CTSM parameter file {orig_pamfile} not found")
        raise FileNotFoundError(f"Original CTSM parameter file {orig_pamfile} not found")

    ctsm_orig = xr.open_dataset(orig_pamfile, decode_cf=False)
    logging.debug(f"CTSM parameter file keys: {list(ctsm_orig.keys())}")
    for pam, new_value in pam_change_dict.items():
        logging.debug(f"Processing parameter: {pam}")
        if pam not in ctsm_orig.keys():
            logging.warning(f"Parameter {pam} not found in CTSM file {orig_pamfile}")
            continue
        logging.debug(f"Parameter {pam} shape: {ctsm_orig[pam].shape}")
        logging.debug(f"Parameter {pam} original value: {ctsm_orig[pam].values}")
        if isinstance(ctsm_orig[pam], abc.Sequence) and not isinstance(ctsm_orig[pam], str):
            logging.debug(f"Parameter {pam} is sequence - applying scaling factor {new_value}")
            ctsm_orig[pam] = new_value * ctsm_orig[pam]
        else:
            logging.debug(f"Parameter {pam} is scalar - setting new value {new_value}")
            ctsm_orig[pam] = new_value

    validate_file(file_path=file_dump, expected_suffix=".nc", description="Generated CTSM parameter file", new_file=True)
    logging.debug(f"Generated CTSM parameter file: {file_dump}")
    ctsm_orig.to_netcdf(file_dump)

    return Path(file_dump).resolve()

def make_new_fates_pamfile(
    pam_change_dict:    dict,
    orig_pamfile:       str | Path,
    file_dump:          str | Path = "fates_pamfile.nc"
) -> Path:
    """Make a new fates pamfile for the PPE, by changing parameters as
    specified in pam_change_dict.

    Parameters
    ----------
    pam_change_dict : dict
        Dictionary with parameter names as keys and new values or scaling
        factors as values. The pam_change_dict has parameter should have
        name of parameter to change as key, and change value as value.
        For scalar parameters this is assumed to be the new value of
        the parameter. For vector parameters the value is assumed to
        be a scaling value to scale the value in the original file with.
    orig_pamfile : str | Path
        Path to the original FATES parameter file to be modified.
    file_dump : str | Path, optional
        Path to save the new FATES parameter file, by default "fates_pamfile.nc".

    Returns
    -------
    Path
        Path to the new FATES parameter file.

    Raises
    ------
    FileNotFoundError
        If the original FATES parameter file is not found.
    """

    if not Path(orig_pamfile).exists():
        logging.error(f"Original FATES parameter file {orig_pamfile} not found")
        raise FileNotFoundError(f"Original FATES parameter file {orig_pamfile} not found")

    fates_orig = xr.open_dataset(orig_pamfile)
    logging.debug(f"FATES parameter file dimensions: {fates_orig.dims}")
    for pam, new_value in pam_change_dict.items():
        logging.debug(f"Processing parameter: {pam}")
        if pam not in fates_orig.keys():
            logging.warning(f"Parameter {pam} not found in FATES file {orig_pamfile}")
            continue
        if fates_orig[pam].shape[0] > 1:
            logging.debug(f"Parameter {pam} is sequence - applying scaling factor {new_value}")
            fates_orig[pam] = new_value * fates_orig[pam]
        else:
            logging.debug(f"Parameter {pam} is scalar - setting new value {new_value}")
            fates_orig[pam] = new_value

    validate_file(file_path=file_dump, expected_suffix=".nc", description="Generated FATES parameter file", new_file=True)
    logging.debug(f"Generated FATES parameter file: {file_dump}")
    fates_orig.to_netcdf(file_dump)

    return Path(file_dump).resolve()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Running parameter file generation tests")
    make_new_ctsm_pamfile(
        {
            "frac_sat_soil_dsl_init": 0.7,
            "d_max": 43.
        },
        orig_pamfile="/cluster/shared/noresm/inputdata/lnd/clm2/paramdata/ctsm60_params.5.3.045_noresm_v14_c251031.nc"
    )
    make_new_fates_pamfile(
        {
            "fates_leaf_stomatal_slope_medlyn": 1.1,
            "fates_mort_hf_sm_threshold":0.9,
            "fates_turb_z0mr": 0.85
        },
        orig_pamfile="/cluster/shared/noresm/inputdata/lnd/clm2/paramdata/fates_params_sci.1.85.1_api.40.0.0_14pft_nor_sci1_api1_c251031.nc"
    )