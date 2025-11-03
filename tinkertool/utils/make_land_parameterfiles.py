import os
import sys

import collections.abc

import xarray as xr

def make_new_ctsm_pamfile(pam_change_dict, orig_pamfile = "/cluster/shared/noresm/inputdata/lnd/clm2/paramdata/ctsm60_params.5.3.045_noresm_v14_c251031.nc", file_dump = "ctsm_pamfile.nc"):
    """
    Make a new ctsn pamfile for the PPE,

    The pam_change_dict has parameter should have name of parameter to change as key, and change value as value. For scalar parameters this is
    assumed to be the new value of the parameter. For vector parameters the value is assumed to be a scaling value to scale the value in the original file with
    """
    if not os.path.exists(orig_pamfile):
        print(f"Original ctsm parameterfile {orig_pamfile} not found")
        raise FileNotFoundError(f"Original ctsm parameterfile {orig_pamfile} not found")

    ctsm_orig = xr.open_dataset(orig_pamfile, decode_cf=False)
    print(ctsm_orig.keys())
    for pam, new_value in pam_change_dict.items():
        print(pam)
        if pam not in ctsm_orig.keys():
            print(f"Parameter {pam} not in ctsm file {orig_pamfile}")
            continue
        print(ctsm_orig[pam].shape)
        print(ctsm_orig[pam])
        if isinstance(ctsm_orig[pam], collections.abc.Sequence) and not isinstance(ctsm_orig[pam], str):
            print(f"parameter {pam} is sequence")
            ctsm_orig[pam] = new_value * ctsm_orig[pam]
        else:
            print(f"parameter {pam} is number")
            ctsm_orig[pam] = new_value

    ctsm_orig.to_netcdf("ctsm_pamfile.nc")

        

def make_new_fates_pamfile(pam_change_dict, orig_pamfile = "/cluster/shared/noresm/inputdata/lnd/clm2/paramdata/fates_params_sci.1.85.1_api.40.0.0_14pft_nor_sci1_api1_c251031.nc"):
    """
    Make a new fates pamfile for the PPE,

    The pam_change_dict has parameter should have name of parameter to change as key, and change value as value. For scalar parameters this is
    assumed to be the new value of the parameter. For vector parameters the value is assumed to be a scaling value to scale the value in the original file with
    """

    if not os.path.exists(orig_pamfile):
        print(f"Original ctsm parameterfile {orig_pamfile} not found")
        raise FileNotFoundError(f"Original ctsm parameterfile {orig_pamfile} not found")

    fates_orig = xr.open_dataset(orig_pamfile)
    print(fates_orig)
    for pam, new_value in pam_change_dict.items():
        print(pam)
        if pam not in fates_orig.keys():
            print(f"Parameter {pam} not in ctsm file {orig_pamfile}")
            continue
        if fates_orig[pam].shape[0] > 1:
            print(f"parameter {pam} is sequence")
            fates_orig[pam] = new_value * fates_orig[pam]
        else:
            print(f"parameter {pam} is number")
            fates_orig[pam] = new_value

    fates_orig.to_netcdf("fates_pamfile.nc")

if __name__ == '__main__':
    print("Add in tests")
    make_new_ctsm_pamfile(
        {
            "frac_sat_soil_dsl_init": 0.7,
            "d_max": 43.
        })
    make_new_fates_pamfile(
        {
            "fates_leaf_stomatal_slope_medlyn": 1.1,
            "fates_mort_hf_sm_threshold":0.9,
            "fates_turb_z0mr": 0.85
        })