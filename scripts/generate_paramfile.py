import argparse as ap
import configparser
import copy
from datetime import datetime

import numpy as np
import pkg_resources
import scipy.stats as stc
import xarray as xr
from tinkertool.utils import make_chem_in

config_path = pkg_resources.resource_filename('config','default_param_ranges.ini')

def scale_values(values, a, b):
    "Scale values from [0, 1] to [a, b] range"
    return a + (b - a) * values

def read_config(config_file):
    with open(config_file) as f:
        config = configparser.ConfigParser()
        config.read_file(f)
    return copy.copy(config)

# Define CLI for creating the hypercube parameter file
def main():
    global config_path
    parser = ap.ArgumentParser(
        description="Generates a Latin Hyper Cube parameter file for PPE experiment")
    parser.add_argument("param_file_outpath", type=str,
        help="Path to the output parameter file")
    parser.add_argument("--param-ranges-file", "-prange", type=str, default=None,
        help="Path to the parameter ranges file, default None will use NorESMTinkerTool/config/default_param_ranges.ini")
    parser.add_argument("--nmb-sim", type=int, default=30,
        help="Number of ensemble members, default 30")
    parser.add_argument("--optimization", "-opt", type=str, default=None,
        help="Whether to enable optimazation after sampling, valid random-cd or lloyd. Default None.")
    parser.add_argument("--avoid-scramble", "-asc", action="store_true",
        help="Overwrite the default scramble of hypercube, i.e. scramble=False to center samples within cells of a multi-dimensional grid. If it is not called, samples are randomly placed within cells of the grid.")
    parser.add_argument("--params", "-p", nargs="+", type=str,
        help="List of parameters to be sampled, have to be defined in --param-ranges-file. If unscpecifiend all parameters in --param-ranges-file will be used")
    parser.add_argument("--assume-component", "-ac", type=str, default='cam',
        help="Assume component for parameter. This is used if component is not specified for an entry in --param-ranges-file. Default is 'cam'.")
    parser.add_argument("--exclude-default", "-exd", action="store_true",
        help="Whether to exclude the default parameter value in the output file in nmb_sim=0. Using this flag will skip nmb_sim=0. Default is to include default value.")
    parser.add_argument("-v", "--verbose", action="count", default=0,
        help="Increase verbosity level (use -v, or -vv for more detail)"
    )
    args = parser.parse_args()
    param_file_outpath = args.param_file_outpath
    # Create a hypercube for five parameters with 30 ensemble members
    nmb_sim =args.nmb_sim
    if args.param_ranges_file:
        config_path = args.param_ranges_file
    print("Reading parameter ranges from", config_path)
    config = read_config(config_path)

    if args.params:
        params = args.params
        nparams = len(params)
    else:
        params = config.sections()
        nparams = len(params)
    if verbose:
        print(f"{'Number of parameters'.ljust(width)}:", nparams)
        print(f"{'Parameters to be sampled'.ljust(width)}:", params)
    # --assume-components
    assumed_esm_component = args.assume_component
    if verbose:
        print(f"{'Assume component'.ljust(width)}:", assumed_esm_component)
    # --exclude_default
    exclude_default = args.exclude_default
    if exclude_default:
        nmb_sim_dim = np.arange(1, nmb_sim+1)
        if verbose:
            print(f"{'Excluding defaults, nmb_sim_dim'.ljust(width)}: [1, {nmb_sim}]",)
    else:
        optimization = None
    

    hypc = stc.qmc.LatinHypercube(nparams, scramble=args.scramble, optimization=optimization)
    hyp_cube_parmas=hypc.random(nmb_sim) 

    sample_points = {}
    # Scale the values to the parameter ranges
    for i, param in enumerate(params): 
        pdata = config[param]
        if pdata.get("scale_fact", None):
            minv = float(pdata["default"]) - float(pdata["default"])*float(pdata["scale_fact"])
            maxv = float(pdata["default"]) + float(pdata["default"])*float(pdata["scale_fact"])
        else:
            minv = float(pdata["min"])
            maxv = float(pdata["max"])

        if pdata.get("sampling") == 'log':
            out_array = np.zeros(nmb_sim+1)
            out_array[0] = float(pdata["default"])
            long_vals = scale_values(hyp_cube_parmas[:,i], np.log10(minv), np.log10(maxv))
            out_array[1:] = 10**long_vals


        else:
            out_array = np.zeros(nmb_sim+1) # Add one extra value to include the default value
            out_array[0] = float(pdata["default"])
            out_array[1:] = scale_values(hyp_cube_parmas[:,i], minv, maxv)
        if pdata.get("ndigits", None):
            out_array = np.around(out_array, int(pdata["ndigits"]))
        sample_points[param] = (["nmb_sim"],out_array)
    # Generate chemistry mech files
    chem_mech_in = []
    if sample_points.get("SOA_y_scale_chem_mech_in", None):
        SOA_y_scale_chem_mech_in = sample_points["SOA_y_scale_chem_mech_in"]
        
        for v in SOA_y_scale_chem_mech_in[1]:
            outfile = make_chem_in.generate_chem_in_ppe(v)
            print(outfile)
            chem_mech_in.append(outfile)

        del sample_points["SOA_y_scale_chem_mech_in"]

    out_ds = xr.Dataset(
        data_vars = sample_points,
        coords={'nmb_sim':nmb_sim_dim})

    for param in out_ds.data_vars:
        out_ds[param].attrs['description'] = config[param].get('description', 'No description available')
        out_ds[param].attrs['default'] = config[param].get('default', 'No default value available')
        out_ds[param].attrs['sampling'] = config[param].get('sampling', 'No sampling method available')
        out_ds[param].attrs['esm_component'] = config[param].get('esm_component', assumed_esm_component)

    # Add variables with irregular names
    if chem_mech_in:
        out_ds['chem_mech_in'] = (['nmb_sim'], chem_mech_in)
    current_time = datetime.now().replace(microsecond=0)
    # Assigning to your attribute
    out_ds.attrs['created'] = f"Created " + current_time.strftime('%Y-%m-%d %H:%M:%S')
    out_ds.to_netcdf(param_file_outpath)

if __name__ == "__main__":
    main()