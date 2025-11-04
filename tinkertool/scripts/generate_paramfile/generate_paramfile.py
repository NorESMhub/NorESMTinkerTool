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
    logging.info("> Starting parameter file generation")

    # check if ParameterFileConfig is valid
    logging.debug(f"Checking config: {config.describe(return_string=True)}") # type: ignore
    checked_config: CheckedParameterFileConfig = config.get_checked_and_derived_config()
    log_info_detailed('tinkertool_log', f">> Generating with config: {checked_config.describe(return_string=True)}") # type: ignore

    # Generate Latin Hypercube sample
    logging.debug("Generating Latin Hypercube sample")
    opt_literal = cast("Literal['random-cd','lloyd'] | None", checked_config.optimization)
    interdependent_params = [param for param in checked_config.params if safe_get_param_value(checked_config.param_ranges[param], "interdependent_with") is not None]
    hypc_params = [param for param in checked_config.params if param not in interdependent_params]
    hypc_param_paramindx_map = {param: indx for indx, param in enumerate(hypc_params)}

    hypc = stats.qmc.LatinHypercube(
        len(hypc_param_paramindx_map),
        scramble=checked_config.scramble,
        optimization=opt_literal
    )
    hyp_cube_params = hypc.random(checked_config.nmb_sim)

    logging.debug(f"Hypersample shape ({checked_config.nmb_sim_dim}, n_params - n_interdependent_params): {hyp_cube_params.shape}")

    logging.debug("Scaling the values to the parameter ranges")
    sample_points = {}
    # Scale the values to the parameter ranges
    # and add component information
    for param in checked_config.params:
        pdata = checked_config.param_ranges[param]

        defaultv = safe_get_param_value(pdata, "default")
        assert defaultv is not None, f"Default value for parameter '{param}' cannot be None."

        # Use safe parameter access to handle nan values properly
        scale_fact: float | None = safe_get_param_value(pdata, "scale_fact")
        if scale_fact is not None:
            minv = float(defaultv) - float(defaultv)*float(scale_fact)
            maxv = float(defaultv) + float(defaultv)*float(scale_fact)
        else:
            minv_raw = safe_get_param_value(pdata, "min")
            maxv_raw = safe_get_param_value(pdata, "max")
            assert minv_raw is not None, f"Min value for parameter '{param}' cannot be None when scale_fact is not provided."
            assert maxv_raw is not None, f"Max value for parameter '{param}' cannot be None when scale_fact is not provided."
            minv = float(minv_raw)
            maxv = float(maxv_raw)

        logging.debug(f"Parameter '{param}': min={minv}, max={maxv}, default={defaultv}, scale_fact={scale_fact}")

        # check what index in hyp_cube_params to use
        # if the param is not interdependent, use hypc_param_paramindx_map[param]
        # if it is interdependent use the index of the param
        # that it is interdependent with
        param_to_index_with = param
        if param not in hypc_param_paramindx_map:
            assert param in interdependent_params, f"Parameter '{param}' not found in hypc_param_paramindx_map or interdependent_params."
            param_to_index_with = safe_get_param_value(pdata, "interdependent_with")
            assert param_to_index_with is not None, f"Parameter '{param}' is interdependent but 'interdependent_with' is None."
        i_use = hypc_param_paramindx_map[param_to_index_with]
        logging.debug(f"Parameter '{param}' uses index {i_use} from hyp_cube_params.")

        sampling_method = safe_get_param_value(pdata, "sampling")
        if sampling_method == 'log':
            out_array = np.zeros(len(checked_config.nmb_sim_dim))
            long_vals = scale_values(hyp_cube_params[:,i_use], np.log10(minv), np.log10(maxv))
            if checked_config.exclude_default:
                out_array = 10**long_vals
            else:
                out_array[0] = float(pdata["default"])
                out_array[1:] = 10**long_vals

        elif sampling_method == 'linear':
            out_array = np.zeros(len(checked_config.nmb_sim_dim))
            long_vals = scale_values(hyp_cube_params[:,i_use], minv, maxv)
            if checked_config.exclude_default:
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

                log_info_detailed('tinkertool_log', f"{outfile} generated with SOA_y_scale_chem_mech_in = {scale_factor}")
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
