#!/usr/bin/env python3
      
import os, sys
from netCDF4 import Dataset
from itertools import islice
import argparse as ap
import configparser

with open('../../../config/default_simulation_setup.ini') as f:
    config = configparser.ConfigParser()
    config.read_file(f)
cesmroot = config['create_case']['cesmroot']

if cesmroot is None:
    raise SystemExit("ERROR: CESM_ROOT must be defined in environment")
_LIBDIR = os.path.join(cesmroot,"cime","scripts","Tools")
sys.path.append(_LIBDIR)
_LIBDIR = os.path.join(cesmroot,"cime","scripts","lib")
sys.path.append(_LIBDIR)

if __name__ == "__main__":
    parser = ap.ArgumentParser(description="Build PPE cases for NorESM")
    parser.add_argument("basecasename", type=str, help="Base case name")
    parser.add_argument("paramfile", type=str, help="NetCDF file with PPE parameters")
    args = parser.parse_args()
    
    basecasename = args.basecasename
    paramfile = args.paramfile
    print ("Starting SCAM PPE case creation, building, and submission script")
    print ("Base case name is {}".format(basecasename))
    print ("Parameter file is "+paramfile)

    # read in NetCDF parameter file
    inptrs = Dataset(paramfile,'r')
    print ("Variables in paramfile:")
    print (inptrs.variables.keys())
    print ("Dimensions in paramfile:")
    print (inptrs.dimensions.keys())
    num_sims = inptrs.dimensions['nmb_sim'].size
    num_vars = len(inptrs.variables.keys())-1
    ensemble_num = inptrs['nmb_sim']
    print('ensemble_num')
    print(ensemble_num)
    print(ensemble_num[0])

    print ("Number of sims = {}".format(num_sims))
    print ("Number of params = {}".format(num_vars))


    # Save a pointer to the netcdf variables
    paramdict = inptrs.variables
    del paramdict['nmb_sim']

    # Create and build the base case that all PPE cases are cloned from
    caseroot = build_base_case(baseroot, basecasename, res,
                                   compset, overwrite)

    # Pass in a dictionary with all of the parameters and their values
    # for each PPE simulation 
    # This code clones the base case, using the same build as the base case,
    # Adds the namelist parameters from the paramfile to the user_nl_cam 
    # file of each new case, does a case.set up, builds namelists, and 
    # submits the runs.

    clone_base_case(caseroot, num_sims, overwrite, paramdict, ensemble_num)

    inptrs.close()