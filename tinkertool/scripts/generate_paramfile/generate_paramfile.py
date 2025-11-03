import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import scipy.stats as stats
import xarray as xr

from tinkertool.scripts.generate_paramfile.config import (
    CheckedParameterFileConfig,
    ParameterFileConfig,
)
from tinkertool.utils.logging import setup_logging
from tinkertool.utils.make_chem_in import generate_chem_in_ppe
from tinkertool.utils.sampling import scale_values


def generate_latin_hypercube_sample_points(config: CheckedParameterFileConfig) -> dict:
    """Generate sample_points using a Latin Hypercube and scale to ranges.

    Returns a dict mapping parameter name -> (["nmb_sim"], values_array).
    """

    logging.debug("> Starting parameter file generation")
    # Generate Latin Hypercube sample
    logging.debug("Generating Latin Hypercube sample")
    hypc = stats.qmc.LatinHypercube(
        config.nparams, scramble=config.scramble, optimization=config.optimization
    )
    hyp_cube_parmas = hypc.random(config.nmb_sim)

    sample_points = {}
    for i, param in enumerate(config.params):
        pdata = config.param_ranges[param]
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

        if pdata.get("sampling") == "log":
            out_array = np.zeros(len(config.nmb_sim_dim))
            long_vals = scale_values(
                hyp_cube_parmas[:, i], np.log10(minv), np.log10(maxv)
            )
            if config.exclude_default:
                out_array = 10 ** long_vals
            else:
                out_array[0] = float(pdata["default"])
                out_array[1:] = 10 ** long_vals

        else:
            out_array = np.zeros(len(config.nmb_sim_dim))
            long_vals = scale_values(hyp_cube_parmas[:, i], minv, maxv)
            if config.exclude_default:
                out_array = long_vals
            else:
                out_array[0] = float(pdata["default"])
                out_array[1:] = long_vals

        if pdata.get("ndigits", None):
            out_array = np.around(out_array, int(pdata["ndigits"]))
        sample_points[param] = (["nmb_sim"], out_array)

    return sample_points


def generate_one_at_a_time_sample_points(config: CheckedParameterFileConfig) -> dict:
    """Generate sample_points for one-at-a-time tests.

    Behavior:
    - The first simulation (index 0) is the default value for all parameters.
    - Subsequent simulations vary one parameter at a time. With its minimum and maximum 
      value for each parameter. Parameters that are not being varied retain their default value.
    """
    n_total = len(config.nmb_sim_dim)
    nparams = len(config.params)
    sample_points = {}

    if n_total <= 1:
        for param in config.params:
            pdata = config.param_ranges[param]
            out_array = np.array([float(pdata.get("default", 0.0))])
            sample_points[param] = (["nmb_sim"], out_array)
        return sample_points

    # Determine how many variation sims per parameter
    n_variations_base = (n_total - 1) // nparams
    remainder = (n_total - 1) % nparams
    variations_per_param = [n_variations_base + (1 if i < remainder else 0) for i in range(nparams)]

    # Prepare matrix filled with defaults
    values = np.zeros((n_total, nparams), dtype=float)
    for j, param in enumerate(config.params):
        pdata = config.param_ranges[param]
        default_val = float(pdata.get("default", 0.0))
        values[:, j] = default_val

    # Fill variation slots
    idx = 1  # start after default
    for j, param in enumerate(config.params):
        pdata = config.param_ranges[param]
        # compute min/max for this parameter
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

        n_var = variations_per_param[j]
        if n_var <= 0:
            continue

        var_vals = np.linspace(minv, maxv, n_var)

        for k in range(n_var):
            if idx >= n_total:
                break
            values[idx, j] = var_vals[k]
            idx += 1

    # Build sample_points dict with rounding
    for j, param in enumerate(config.params):
        pdata = config.param_ranges[param]
        out_array = values[:, j]
        if pdata.get("ndigits", None):
            out_array = np.around(out_array, int(pdata["ndigits"]))
        sample_points[param] = (["nmb_sim"], out_array)

    return sample_points




def generate_chem_mech_files(sample_points: dict, config: CheckedParameterFileConfig) -> list:
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


def generate_paramfile(config: ParameterFileConfig):
    # Set up logging
    setup_logging(config.verbose, config.log_file, config.log_mode)
    logging.info("> Starting parameter file generation")

    # check if ParameterFileConfig is valid
    logging.debug(f"Checking config: {config.describe(return_string=True)}")
    config: CheckedParameterFileConfig = config.get_checked_and_derived_config()
    logging.getLogger().info_detailed(
        f">> Generating with config: {config.describe(return_string=True)}"
    )

    # Create sample points using the requested sampling strategy
    if config.one_at_the_time:
        sample_points = generate_one_at_a_time_sample_points(config)
    else:
        sample_points = generate_latin_hypercube_sample_points(config)

    # Generate chemistry mech files
    if config.change_chem_mech:
        logging.debug("Generating chemistry mechanism files")
        chem_mech_in = generate_chem_mech_files(sample_points, config)

    logging.debug("Creating xarray dataset")
    out_ds = xr.Dataset(data_vars=sample_points, coords={"nmb_sim": config.nmb_sim_dim})

    for param in out_ds.data_vars:
        out_ds[param].attrs["description"] = config.param_ranges[param].get(
            "description", "No description available"
        )
        out_ds[param].attrs["default"] = config.param_ranges[param].get(
            "default", "No default value available"
        )
        out_ds[param].attrs["sampling"] = config.param_ranges[param].get(
            "sampling", "No sampling method available"
        )
        out_ds[param].attrs["esm_component"] = config.param_ranges[param].get(
            "esm_component", config.assumed_esm_component
        )

    # Add variables with irregular names
    print(config.change_chem_mech)
    if config.change_chem_mech and config.perturbed_chem_mech:
        logging.debug("Adding chemistry mechanism files to dataset")
        out_ds["chem_mech_in"] = (["nmb_sim"], chem_mech_in)
    current_time = datetime.now().replace(microsecond=0)
    # Assigning to your attribute
    out_ds.attrs["created"] = f"Created " + current_time.strftime("%Y-%m-%d %H:%M:%S")
    out_ds.to_netcdf(config.param_sample_outpath)

    logging.info(
        f">> Parameter file {config.param_sample_outpath} generated successfully."
    )
