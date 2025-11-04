import logging
import numpy as np
import xarray as xr
import scipy.stats as stats
from pathlib import Path
from datetime import datetime

from tinkertool.utils.custom_logging import setup_logging, log_info_detailed
from tinkertool.utils.sampling import scale_values
from tinkertool.utils.make_chem_in import generate_chem_in_ppe
from tinkertool.scripts.generate_paramfile.config import (
    ParameterFileConfig,
    CheckedParameterFileConfig
)

def _test_ranges(
    minv: float,
    maxv: float,
    param: str,
    out_array: np.ndarray
) -> bool:
    """Test if the generated parameter samples are within the specified ranges.
    Intended for extra checking after rounding and interconnections.

    Parameters
    ----------
    minv : float
        The minimum value for the parameter.
    maxv : float
        The maximum value for the parameter.
    param : str
        The name of the parameter.
    out_array : np.ndarray
        The array of generated parameter samples.

    Returns
    -------
    bool
        True if all samples are within ranges, False otherwise.
    """

    all_within_ranges = True

    for val in out_array:
        if not (minv <= val <= maxv):
            logging.error(f"Parameter '{param}' has value {val} outside of range [{minv}, {maxv}].")
            all_within_ranges = False

    if all_within_ranges:
        logging.debug(f"All values for parameter '{param}' are within the range [{minv}, {maxv}].")
    else:
        logging.warning(f"Some values for parameter '{param}' are outside of the range [{minv}, {maxv}].")

    return all_within_ranges

def generate_paramfile(config: ParameterFileConfig):

    # Set up logging
    setup_logging(config.verbose, config.log_file, config.log_mode)
    logging.info("> Starting parameter file generation")

    # check if ParameterFileConfig is valid
    logging.debug(f"Checking config: {config.describe(return_string=True)}")
    config: CheckedParameterFileConfig = config.get_checked_and_derived_config()
    logging.getLogger('tinkertool_log').info_detailed(f">> Generating with config: {config.describe(return_string=True)}")

    # Generate Latin Hypercube sample
    logging.debug("Generating Latin Hypercube sample")
    hypc = stats.qmc.LatinHypercube(config.nparams, scramble=config.scramble, optimization=config.optimization)
    hyp_cube_parmas = hypc.random(config.nmb_sim)

    logging.debug("Scaling the values to the parameter ranges")
    sample_points = {}
    # Scale the values to the parameter ranges
    # and add component information
    for i, param in enumerate(config.params):
        pdata = config.param_ranges[param]
        if pdata.get("scale_fact", None):
            minv = float(pdata["default"]) - float(pdata["default"])*float(pdata["scale_fact"])
            maxv = float(pdata["default"]) + float(pdata["default"])*float(pdata["scale_fact"])
        else:
            minv = float(pdata["min"])
            maxv = float(pdata["max"])

        if pdata.get("sampling") == 'log':
            out_array = np.zeros(len(config.nmb_sim_dim))
            long_vals = scale_values(hyp_cube_parmas[:,i], np.log10(minv), np.log10(maxv))
            if config.exclude_default:
                out_array = 10**long_vals
            else:
                out_array[0] = float(pdata["default"])
                out_array[1:] = 10**long_vals

        else:
            out_array = np.zeros(len(config.nmb_sim_dim))
            long_vals = scale_values(hyp_cube_parmas[:,i], minv, maxv)
            if config.exclude_default:
                out_array = long_vals
            else:
                out_array[0] = float(pdata["default"])
                out_array[1:] = long_vals
        else:
            err_msg = f"Unknown sampling method '{sampling_method}' for parameter '{param}'. Supported methods are 'log' and 'linear'."
            logging.error(err_msg)
            raise ValueError(err_msg)

        ndigits = safe_get_param_value(pdata, "ndigits")
        if ndigits is not None:
            # Convert to float first, then int to handle strings like '5.0'
            out_array = np.around(out_array, int(float(ndigits)))

        _test_ranges(minv, maxv, param, out_array)
        sample_points[param] = (["nmb_sim"], out_array)

    # Generate chemistry mech files
    if config.change_chem_mech:
        logging.debug("Generating chemistry mechanism files")

        chem_mech_in = []
        if sample_points.get("SOA_y_scale_chem_mech_in", None):
            SOA_y_scale_chem_mech_in = sample_points["SOA_y_scale_chem_mech_in"]

            for scale_factor in SOA_y_scale_chem_mech_in[1]:
                outfile = generate_chem_in_ppe(
                    scale_factor=scale_factor,
                    input_file=config.chem_mech_file,
                    outfolder_base=config.tinkertool_output_dir,
                    outfolder_name='chem_mech_files',
                    verbose=True if config.verbose > 2 else False,
                )
                chem_mech_in.append(outfile)

                logging.getLogger('tinkertool_log').info_detailed(f"{outfile} generated with SOA_y_scale_chem_mech_in = {scale_factor}")

            del sample_points["SOA_y_scale_chem_mech_in"]

    logging.debug("Creating xarray dataset")
    out_ds = xr.Dataset(
        data_vars = sample_points,
        coords={'nmb_sim':config.nmb_sim_dim})

    for param in out_ds.data_vars:
        out_ds[param].attrs['description'] = config.param_ranges[param].get('description', 'No description available')
        out_ds[param].attrs['default'] = config.param_ranges[param].get('default', 'No default value available')
        out_ds[param].attrs['sampling'] = config.param_ranges[param].get('sampling', 'No sampling method available')
        out_ds[param].attrs['esm_component'] = config.param_ranges[param].get('component', config.assumed_esm_component).lower()

    # Add variables with irregular names
    if config.change_chem_mech:
        out_ds['chem_mech_in'] = (['nmb_sim'], chem_mech_in)
    current_time = datetime.now().replace(microsecond=0)
    # Assigning to your attribute
    out_ds.attrs['created'] = f"Created " + current_time.strftime('%Y-%m-%d %H:%M:%S')
    out_ds.to_netcdf(config.param_sample_outpath)

    logging.info(f">> Parameter file {config.param_sample_outpath} generated successfully.")
