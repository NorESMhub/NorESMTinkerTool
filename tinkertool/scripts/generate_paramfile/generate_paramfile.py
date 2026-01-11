import logging
import numpy as np
import xarray as xr
import scipy.stats as stats
from datetime import datetime
from typing import cast, Literal

from tinkertool.utils.custom_logging import log_info_detailed
from tinkertool.utils.sampling import scale_values
from tinkertool.utils.make_chem_in import generate_chem_in_ppe
from tinkertool.utils.make_land_parameterfiles import (
    make_new_ctsm_pamfile,
    make_new_fates_pamfile
)
from tinkertool.utils.read_files import safe_get_param_value
from tinkertool import VALID_COMPONENTS
from tinkertool.scripts.generate_paramfile import PARAMFILE_INPUT_TYPES
from tinkertool.scripts.generate_paramfile.config import (
    ParameterFileConfig
)

VALID_SAMPLING_METHODS = ['linear', 'log']

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

def generate_chem_mech_files(sample_points: dict, config: ParameterFileConfig) -> list:
    """Generate chemistry mechanism files and return list of generated file paths.

    This mutates `sample_points` by removing the
    'SOA_y_scale_chem_mech_in' entry when present.
    """
    
    chem_mech_in = []
    if sample_points.get("SOA_y_scale_chem_mech_in", None):
        SOA_y_scale_chem_mech_in = sample_points["SOA_y_scale_chem_mech_in"]

        for scale_factor in SOA_y_scale_chem_mech_in[1]:
            outfile = generate_chem_in_ppe(
                scale_factor=scale_factor,
                input_file=config.chem_mech_file,
                outfolder_base=config.tinkertool_output_dir,
                outfolder_name="chem_mech_files",
                verbose=True if config.verbose > 2 else False,
            )
            chem_mech_in.append(outfile)

            logging.getLogger().info_detailed(
                f"{outfile} generated with SOA_y_scale_chem_mech_in = {scale_factor}"
            )

        # remove the entry so it is not written to the final dataset
        del sample_points["SOA_y_scale_chem_mech_in"]

    return chem_mech_in
def generate_land_model_param_files(
    sample_points: dict,
    sample_points_with_files: dict,
    checked_config: ParameterFileConfig
) -> None:
    
    ctsm_fates_paramfile_info = []
    if checked_config.change_ctsm_params:
        CTSM_param_file_params = [
            param for param in checked_config.params
            if safe_get_param_value(checked_config.param_ranges[param], "input_type") == "CTSM_param_file"
        ]
        ctsm_fates_paramfile_info.append(("CTSM_param_file", 'paramfile', CTSM_param_file_params, make_new_ctsm_pamfile))
    if checked_config.change_fates_params:
        FATES_param_file_params = [
            param for param in checked_config.params
            if safe_get_param_value(checked_config.param_ranges[param], "input_type") == "FATES_param_file"
        ]
        ctsm_fates_paramfile_info.append(("FATES_param_file", 'fates_paramfile', FATES_param_file_params, make_new_fates_pamfile))
    if not ctsm_fates_paramfile_info:
        return  # Nothing to do, so exit early.


    logging.debug("Generating land model parameter files")
    for param_type, user_nl_kw, param_group, make_new_param_file in ctsm_fates_paramfile_info:
        # create new section in the ConfigParser object (if it doesn't exist)
        if not checked_config.param_ranges.has_section(user_nl_kw):
            checked_config.param_ranges.add_section(user_nl_kw)
        pg_param_ranges = checked_config.param_ranges[user_nl_kw]

        pam_filepaths = []
        for sim_indx in checked_config.nmb_sim_dim:
            pam_change_dict = {}
            for param in param_group:
                pam_change_dict[param] = sample_points[param][1][sim_indx]  # Access values array from (dims, values) tuple
            if pam_change_dict:
                if param_type == 'CTSM_param_file':
                    orig_pamfile = checked_config.ctsm_default_param_file

                elif param_type == 'FATES_param_file':
                    orig_pamfile = checked_config.fates_default_param_file
                    if orig_pamfile is None:
                        raise ValueError("FATES default parameter file path is not set in the configuration:\n"
                                        "Please provide a valid path to the FATES default parameter file.")
                else:
                    raise ValueError(f"Unknown parameter file type '{param_type}'.")
                save_path = checked_config.tinkertool_output_dir.joinpath(
                    user_nl_kw,
                    f"{user_nl_kw}_file_sim{sim_indx}.nc"
                ).resolve()
                # Ensure directory exists before creating the file
                save_path.parent.mkdir(parents=True, exist_ok=True)
                new_pamfile = make_new_param_file(
                    pam_change_dict,
                    orig_pamfile=orig_pamfile,
                    file_dump=save_path
                )
                pam_filepaths.append(str(new_pamfile))
                log_info_detailed('tinkertool_log', f"{new_pamfile} generated with changes: {pam_change_dict}")
        if pam_filepaths:
            sample_points_with_files[user_nl_kw] = (['nmb_sim'], pam_filepaths)
            # add attribute info
            pg_defaults, pg_newvals, pg_sampling, pg_input_type, pg_interdependent_with, pg_esm_component = {}, {}, {}, {}, {}, {}
            for param in param_group:
                pdata = checked_config.param_ranges[param]
                pg_defaults[param] = pdata['default']
                pg_newvals[param] = sample_points[param][1].copy()  # Access values array from (dims, values) tuple
                pg_sampling[param] = safe_get_param_value(pdata, 'sampling', 'No sampling method available')
                pg_input_type[param] = safe_get_param_value(pdata, 'input_type', '')
                pg_interdependent_with[param] = safe_get_param_value(pdata, 'interdependent_with', '')
                pg_esm_component[param] = safe_get_param_value(pdata, 'esm_component', '')
                del sample_points_with_files[param]
            pg_param_ranges['default'] = ",\n".join([f"{param}: {pg_defaults[param]}" for param in param_group])
            pg_param_ranges['sampling'] = ",\n".join([f"{param}: {pg_sampling[param]}" for param in param_group])
            # input_type should be same for all params in group
            input_type = [pg_input_type[param] for param in param_group]
            if not all(it == input_type[0] for it in input_type):
                raise ValueError(f"Parameters in group {param_group} have differing input_types: {input_type}")
            pg_param_ranges['input_type'] = input_type[0]
            pg_param_ranges['interdependent_with'] = ",\n".join([f"{param}: {pg_interdependent_with[param]}" for param in param_group])
            esm_component = [pg_esm_component[param] for param in param_group]
            if not all(it == esm_component[0] for it in esm_component):
                raise ValueError(f"Parameters in group {param_group} have differing esm_component: {esm_component}")
            pg_param_ranges['esm_component'] = esm_component[0]
            pg_param_ranges['description'] = f"{param_type} file perturbing parameters:\n" + \
                ",\n".join([f"{param}, default -> new value: {pg_defaults[param]} -> {pg_newvals[param]}" for param in param_group])


def generate_latin_hypercube_sample_points(checked_config: ParameterFileConfig) -> dict:
    """Generate sample_points using a Latin Hypercube and scale to ranges.

    Returns a dict mapping parameter name -> (["nmb_sim"], values_array).
    """
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
        inverse_scaling = False
        param_to_index_with = param
        if param not in hypc_param_paramindx_map: # then it is interdependent
            assert param in interdependent_params, f"Parameter '{param}' not found in hypc_param_paramindx_map or interdependent_params."
            param_to_index_with = safe_get_param_value(pdata, "interdependent_with")
            # check if we are to use inverse scaling by checking for
            # "-" prefix/first character
            if param_to_index_with.startswith("-"):
                param_to_index_with = param_to_index_with[1:]  # remove the "-" character
                logging.debug(f"Parameter '{param}' is interdependent with '{param_to_index_with}' using inverse scaling.")
                # Inverse scaling: we will later do maxv - scaled_value + minv
                # to flip the scaling
                # This is handled in scale_values function by passing minv and maxv swapped
                minv, maxv = maxv, minv
                inverse_scaling = True
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
            err_msg = f"Unknown sampling method '{sampling_method}' for parameter '{param}'. Supported methods are {', '.join(VALID_SAMPLING_METHODS)}."
            logging.error(err_msg)
            raise ValueError(err_msg)

        ndigits = safe_get_param_value(pdata, "ndigits")
        if ndigits is not None:
            # Convert to float first, then int to handle strings like '5.0'
            out_array = np.around(out_array, int(float(ndigits)))

        if inverse_scaling:
            _test_ranges(maxv, minv, param, out_array)
        else:
            _test_ranges(minv, maxv, param, out_array)
        sample_points[param] = (["nmb_sim"], out_array)

    return sample_points


def generate_one_at_a_time_sample_points(checked_config: ParameterFileConfig) -> dict:
    """Generate sample_points for one-at-a-time tests.

    Behavior:
    - The first simulation (index 0) is the default value for all parameters.
    - Subsequent simulations vary one parameter at a time. With its minimum and maximum 
      value for each parameter. Parameters that are not being varied retain their default value.
    """
    n_total = len(checked_config.nmb_sim_dim)
    nparams = len(checked_config.params)
    sample_points = {}

    # Determine how many variation sims per parameter
    n_variations_base = (n_total - 1) // nparams
    remainder = (n_total - 1) % nparams
    variations_per_param = 2

    # Prepare matrix filled with defaults
    values = np.zeros((n_total, nparams), dtype=float)

    for j, param in enumerate(checked_config.params):
        pdata = checked_config.param_ranges[param]
        default_val = float(pdata.get("default", None))
        if default_val is None:
            raise ValueError(f"Parameter {param} has no default value defined.")
        values[:, j] = default_val

    if checked_config.exclude_default == False:
        idx = 1  # start after default
    else:
        idx = 0  # start at beginning
    for j, param in enumerate(checked_config.params):
        pdata = checked_config.param_ranges[param]
        
        if pdata.get("scale_fact", None):
            minv = float(pdata["default"]) - float(pdata["default"]) * float(
                pdata["scale_fact"]
            )
            maxv = float(pdata["default"]) + float(pdata["default"]) * float(
                pdata["scale_fact"]
            )
        else:
            minv = float(pdata["min"])
            maxv = float(pdata["max"])

        n_var = variations_per_param

        var_vals = np.linspace(minv, maxv, n_var)
        for k in range(n_var):
            if idx >= n_total:
                break
            values[idx, j] = var_vals[k]
            idx += 1

    # Build sample_points dict with rounding
    for j, param in enumerate(checked_config.params):
        pdata = checked_config.param_ranges[param]
        out_array = values[:, j]
        if pdata.get("ndigits", None):
            out_array = np.around(out_array, int(pdata["ndigits"]))
        sample_points[param] = (["nmb_sim"], out_array)

    return sample_points


def generate_paramfile(config: ParameterFileConfig):
    # Set up logging
    logging.info("> Starting parameter file generation")

    # check if ParameterFileConfig is valid
    logging.debug(f"Checking config: {config.describe(return_string=True)}") # type: ignore
    checked_config: ParameterFileConfig = config.get_checked_and_derived_config()
    log_info_detailed('tinkertool_log', f">> Generating with config: {checked_config.describe(return_string=True)}") # type: ignore
    n_total = len(checked_config.nmb_sim_dim)
    if checked_config.method == 'one_at_a_time' or checked_config.method == 'oat':
        sample_points = generate_one_at_a_time_sample_points(checked_config)
    elif n_total <= 1:
        for param in checked_config.params:
            pdata = checked_config.param_ranges[param]
            out_array = np.array([float(pdata.get("default", 0.0))])
            sample_points[param] = (["nmb_sim"], out_array)
    elif checked_config.method == 'latin_hypercube' or checked_config.method == 'lh':
        sample_points = generate_latin_hypercube_sample_points(checked_config)
    else:
        raise ValueError(f"Invalid sampling method '{checked_config.method}'.")

    sample_points_with_files = sample_points.copy()

    if config.change_chem_mech:
        logging.debug("Generating chemistry mechanism files")
        chem_mech_in = generate_chem_mech_files(sample_points, config)

    generate_land_model_param_files(sample_points, sample_points_with_files, checked_config)
    
    logging.debug("Creating xarray dataset")
    raw_ds = xr.Dataset(
        data_vars = sample_points,
        coords={'nmb_sim':checked_config.nmb_sim_dim}
    )
    out_ds = xr.Dataset(
        data_vars = sample_points_with_files,
        coords={'nmb_sim':checked_config.nmb_sim_dim}
    )

    for ds in [raw_ds, out_ds]:
        for param in ds.data_vars:
            pdata = checked_config.param_ranges[str(param)]
            ds[param].attrs['description'] = safe_get_param_value(pdata, 'description', 'No description available')
            ds[param].attrs['default'] = safe_get_param_value(pdata, 'default', 'No default value available')
            ds[param].attrs['sampling'] = safe_get_param_value(pdata, 'sampling', 'No sampling method available')

            input_type = safe_get_param_value(pdata, 'input_type', "user_nl")
            assert not isinstance(input_type, str) or input_type.lower() in [it.lower() for it in PARAMFILE_INPUT_TYPES], \
                f"Invalid input type '{input_type}, type({type(input_type)})' for parameter '{param}'. Supported types are: {PARAMFILE_INPUT_TYPES}."
            ds[param].attrs['input_type'] = input_type
            ds[param].attrs['interdependent_with'] = safe_get_param_value(pdata, "interdependent_with", "")

            component = pdata.get('esm_component')
            if not isinstance(component, str):
                err_msg = f"The component passed to param {param} is of type {type(component)}, expected type str"
                logging.error(err_msg)
                raise TypeError(err_msg)
            if component.lower() not in VALID_COMPONENTS:
                err_msg = f"Invalid component '{component}' for parameter '{param}'. Supported components are: {VALID_COMPONENTS}."
                logging.error(err_msg)
                raise ValueError(err_msg)
            ds[param].attrs['esm_component'] = component.lower()

    # Add variables with irregular names
    if checked_config.change_chem_mech:
        out_ds['chem_mech_in'] = (['nmb_sim'], chem_mech_in)
    current_time = datetime.now().replace(microsecond=0)
    # Assigning to your attribute
    for ds in [raw_ds, out_ds]:
        ds.attrs['created'] = f"Created " + current_time.strftime('%Y-%m-%d %H:%M:%S')
    raw_ds.to_netcdf(checked_config.param_sample_outpath.with_suffix('.raw.nc'))
    out_ds.to_netcdf(checked_config.param_sample_outpath.with_suffix('.nc'))

    logging.info(f">> Raw parameter file (only numbers) {checked_config.param_sample_outpath.with_suffix('.raw.nc')} generated successfully.")
    logging.info(f">> Parameter file (with filepaths) {checked_config.param_sample_outpath.with_suffix('.nc')} generated successfully.")
