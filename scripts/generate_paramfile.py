import xarray as xr
import numpy as np
import scipy.stats as stc
from tinkertool.utils import make_chem_in
import argparse as ap
import configparser
import pkg_resources
import os, sys
import copy
import argparse as ap
from datetime import datetime

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
    parser.add_argument("param_file_outpath", type=str, help="Path to the output parameter file")
    parser.add_argument("--param-ranges-file", "-prange", default=None, type=str, help="Path to the parameter ranges file")
    parser.add_argument("--nmb-sim", default=30, type=int, help="Number of ensemble members")
    parser.add_argument("--optimization", "-opt", type=str,default=None, 
                        help="Whether to enable optimazation after sampling, valid random-cd or lloyd")
    parser.add_argument("--scramble", "-sc", action="store_false", 
                        help="When False, center samples within cells of a multi-dimensional grid. Otherwise, samples are randomly placed within cells of the grid.")
    parser.add_argument("--params", "-p", nargs="+", type=str, 
                        help="List of parameters to using in the sampling, have to be defined in the parameter ranges file, else all parameters will be used")

    
    
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
    if args.optimization:
        optimization = args.optimization
    else:
        optimization = None
    

    hypc = stc.qmc.LatinHypercube(nparams, scramble=args.scramble, optimization=optimization)
    hyp_cube_parmas=hypc.random(nmb_sim)

    sample_points = {}
    for i, param in enumerate(params): 
        pdata = config[param]
        if pdata.get("scale_fact", None):
            minv = float(pdata["default"]) - float(pdata["default"])*float(pdata["scale_fact"])
            maxv = float(pdata["default"]) + float(pdata["default"])*float(pdata["scale_fact"])
        else:
            minv = float(pdata["min"])
            maxv = float(pdata["max"])

        if pdata.get("sampling") == 'log':
            long_vals = scale_values(hyp_cube_parmas[:,i], np.log10(minv), np.log10(maxv))
            sample_points[param] = (["nmb_sim"],10**long_vals)
        else:
            sample_points[param] = (["nmb_sim"],scale_values(hyp_cube_parmas[:,i], minv, maxv))        

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
        coords={'nmb_sim':np.arange(nmb_sim)})
    
    for k in out_ds.data_vars:
        out_ds[k].attrs['description'] = config[k].get('description', 'No description available')
        out_ds[k].attrs['default'] = config[k].get('default', 'No default value available')
        out_ds[k].attrs['sampling'] = config[k].get('sampling', 'No sampling method available')
    # Add variables with irregular names
    if chem_mech_in:
        out_ds['chem_mech_in'] = (['nmb_sim'], chem_mech_in)
    current_time = datetime.now().replace(microsecond=0)
    # Assigning to your attribute
    out_ds.attrs['created'] = f"Created " + current_time.strftime('%Y-%m-%d %H:%M:%S')
    out_ds.to_netcdf(param_file_outpath)

if __name__ == "__main__":
    main()