#!/usr/bin/env python3
      
import os, sys
from netCDF4 import Dataset
from itertools import islice
import argparse as ap
import configparser
import pkg_resources
import copy
from pathlib import Path
# %%
config_path = pkg_resources.resource_filename('config','default_simulation_setup.ini')
with open(config_path) as f:
    config = configparser.ConfigParser()
    config.read_file(f)

def add_CIME_paths_and_import(cesmroot):
    _LIBDIR = os.path.join(cesmroot,"cime","scripts","Tools")
    sys.path.append(_LIBDIR)
    _LIBDIR = os.path.join(cesmroot,"cime","scripts","lib")
    sys.path.append(_LIBDIR)
    try:
        from tinkertool.setup.case import (build_base_case,
                                    clone_base_case)
    except ImportError:
        print(f"ERROR: CIME not found in {cesmroot}, update CESMROOT environment variable or set --cesm-root")
    global build_base_case, clone_base_case    

def read_config(config_file):
    with open(config_file) as f:
        config = configparser.ConfigParser()
        config.read_file(f)
    return copy.copy(config)

def main():
    global config
    parser = ap.ArgumentParser(
                    description="Build PPE cases for NorESM")
    parser.add_argument("basecasename", type=str, help="Base case name")
    parser.add_argument("paramfile", type=str, help="NetCDF file with PPE parameters")
    parser.add_argument("--overwrite", "-o", action="store_true", help="Overwrite existing cases")
    parser.add_argument("--pdim", default="nmb_sim", type=str, help="Name of dimension for number of simulations")
    parser.add_argument("--config-setup", "-cs", default="./simulation_setup.ini", type=str, help="Path to user defined configuration file")
    parser.add_argument("--base-case-id", "-bci", default="000", type=str, help="Base case identifier")
    parser.add_argument("--nl-cam", "-cam", default="./user_nl_cam.ini", type=str, help="Path to user defined namelist file (CAM)")
    parser.add_argument("--nl-cpl", "-cpl", default="./user_nl_cpl.ini", type=str, help="Path to user defined namelist file (CLP)")
    parser.add_argument("--nl-cice", "-cice", default="./user_nl_cice.ini", type=str, help="Path to user defined namelist file (CICE)")
    parser.add_argument("--nl-clm", "-ice", default="./user_nl_clm.ini", type=str, help="Path to user defined namelist file (CLM)")
    parser.add_argument("--nl-docn", "-docn", default="./user_nl_docn.ini", type=str, help="Path to user defined namelist file (DOCN)")
    parser.add_argument("--build-base-only", action="store_true", help="Only build the base case")
    parser.add_argument("--cesm-root", "-cr", default=None, type=str, help="Path to CESM root directory, if not provided, will use CESMROOT environment variable")
    args = parser.parse_args()
    
    basecasename = args.basecasename
    paramfile = args.paramfile
    overwrite = args.overwrite
    pdim = args.pdim
    config_setup = args.config_setup
    cesmroot = args.cesm_root
    if cesmroot is None:
        cesmroot = os.environ.get('CESMROOT')
        if cesmroot is None:
            print("CESM_ROOT not defined in environment, using default from configuration file")
            cesmroot = config['create_case']['cesmroot']
        
    if cesmroot is None:
        raise SystemExit("ERROR: CESM_ROOT must be defined in environment or in configuration file")
    add_CIME_paths_and_import(cesmroot)
    # get namelist names from args
    namelist = [a for a in dir(args) if a.startswith('nl_')]

    namelist_collection_dict = {}

    for nl in namelist:
        temp_nl = getattr(args, nl)
        if not os.path.isfile(temp_nl):
            print(f"WARNING: {temp_nl} not found")
            # could more default namelist files here
            if nl == 'nl_cam':
                user_nl_path = pkg_resources.resource_filename('config','default_control_atm.ini')
                
                print(f"Using default CAM namelist file: {user_nl_path}")
                namelist_collection_dict['nl_cam'] = read_config(user_nl_path)

            elif nl == 'nl_clm':
                user_nl_path = pkg_resources.resource_filename('config','default_control_lnd.ini')
                
                print(f"Using default CLM namelist file: {user_nl_path}")
                namelist_collection_dict['nl_clm'] = read_config(user_nl_path)
        
        else:
            namelist_collection_dict[nl] = read_config(temp_nl)
    if os.path.isfile(config_setup):
        with open(config_setup) as f:
            usr_config = configparser.ConfigParser()
            usr_config.read_file(f)
        config = config.update(usr_config)
    else:
        print("WARNING: Using default configuration file, no user defined configuration file found")

    print ("Starting SCAM PPE case creation, building, and submission script")
    print ("Base case name is {}".format(basecasename))
    print ("Parameter file is "+paramfile)
    # Get path dir where paramfile is located (will look for potential chem_mech.in files there)
    path_paramfile_dir = Path(paramfile).resolve().parent
    # read in NetCDF parameter file
    # %%
    inptrs = Dataset(paramfile,'r')
    print ("Variables in paramfile:")
    print (inptrs.variables.keys())
    print ("Dimensions in paramfile:")
    print (inptrs.dimensions.keys())
    num_sims = inptrs.dimensions[pdim].size
    num_vars = len(inptrs.variables.keys())-1
    ensemble_num = inptrs[pdim]

    print ("Number of sims = {}".format(num_sims))
    print ("Number of params = {}".format(num_vars))
    # %%

    # Save a pointer to the netcdf variables
    paramdict = inptrs.variables

    del paramdict[pdim]

    print ("paramdict keys:", paramdict.keys())
    # %%
    baseroot = config['ppe_settings']['baseroot']
    baseidentifier = config['ppe_settings'].get('baseidentifier', args.base_case_id)

    cesmroot = config['create_case']['cesmroot']
    # Create and build the base case that all PPE cases are cloned from
    # %%
    caseroot = build_base_case(baseroot=baseroot,
                               basecasename=basecasename,
                               overwrite=overwrite,
                               case_settings=config['create_case'],
                               env_run_settings=config['env_run'],
                               env_build_settings=config['env_build'],
                               basecase_startval=baseidentifier,
                               namelist_collection_dict=namelist_collection_dict,
                               cesmroot=cesmroot)
    # Loop over the number of simulations and clone the base case
    if args.build_base_only:
        print("Only building base case")
    else:
        start_num = 1
        for i, idx in zip(range(start_num, num_sims+start_num), ensemble_num):
            print (f"Building case number: {i:03d}")
            ensemble_idx = f"{basecasename}.{i:03d}"
            temp_dict = {k : v[idx] for k,v in paramdict.items()}
            # Special treatment for chem_mech.in changes:
            if 'chem_mech_in' in temp_dict:
                # remove all chem_mech_in keys that are not chem_mech_in (there can anyway only be one chem_mech.in file)
                keys_in_dic = list(temp_dict.keys())
                for v in keys_in_dic:
                    if v[-12:]=='chem_mech_in' and len(v)>12:
                        print(f'Deleting {v} from parameter directory' )
                        del temp_dict[v]
            # %%
            clone_base_case(baseroot,caseroot, overwrite, temp_dict, ensemble_idx, path_base_input = path_paramfile_dir)
            # %%
    inptrs.close()
# %%
if __name__ == "__main__":
    # %%
    main()
    # %%