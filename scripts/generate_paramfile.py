import xarray as xr
import numpy as np
import scipy.stats as stc
from tinkertool.utils import make_chem_in

def scale_values(values, a, b):
    "Scale values from [0, 1] to [a, b] range"
    return a + (b - a) * values

# Create a hypercube for five parameters with 30 ensemble members
nmb_sim = 30
hypc = stc.qmc.LatinHypercube(10)
hyp_cube_parmas=hypc.random(nmb_sim)

# Scale the values of the hypercube to be within the parameter ranges

scaled_emis_fact_in_cmod = scale_values(hyp_cube_parmas[:,0], 0.87,0.98)
dust_emis_fact_vals = scale_values(hyp_cube_parmas[:,1],0.2,1.2)
f_act_conv_coarse_dust_vals= scale_values(hyp_cube_parmas[:,2],.1, .9)
hetfrz_aer_scalfac_vals =  scale_values(hyp_cube_parmas[:,3],.001, .02)
microp_aero_wsub_min_vals = scale_values(hyp_cube_parmas[:,4], 0.001,0.3)
# special treatment for chem_mech.in changes:
SOA_y_scale_chem_mech_in = scale_values(hyp_cube_parmas[:,5], 0.2, 2)
oslo_aero_lifecyclenumbermedianradius_1 = scale_values(hyp_cube_parmas[:,6], 12.5e-9, 37.5e-09)
oslo_aero_lifecyclenumbermedianradius_8 = scale_values(hyp_cube_parmas[:,7], 23.5e-9, 70.5e-9)
oslo_aero_lifeCycleSigma_1 = scale_values(hyp_cube_parmas[:,8], 1.44, 2.16)
oslo_aero_lifeCycleSigma_8 = scale_values(hyp_cube_parmas[:,9], 1.68, 2.52)
chem_mech_in = []
for v in SOA_y_scale_chem_mech_in:
    print(v)
    outfile = make_chem_in.generate_chem_in_ppe(v)
    chem_mech_in.append(outfile)


# Create xarray dataset with all the parameter combinations

out_ds = xr.Dataset(
    data_vars = dict(emis_fact_in_coarse_mode= (["nmb_sim"],scaled_emis_fact_in_cmod),
                     dust_emis_fact=(["nmb_sim"],dust_emis_fact_vals),
                     f_act_conv_coarse_dust=(["nmb_sim"],f_act_conv_coarse_dust_vals),
                     hetfrz_aer_scalfac=(["nmb_sim"],hetfrz_aer_scalfac_vals ),
                     microp_aero_wsub_min= (["nmb_sim"],microp_aero_wsub_min_vals ),
                     SOA_y_scale_chem_mech_in= (["nmb_sim"],SOA_y_scale_chem_mech_in ),
                     chem_mech_in= (["nmb_sim"],chem_mech_in ),
                     ),
    coords={'nmb_sim':np.arange(nmb_sim)})
# Add variables with irregular names
out_ds['oslo_aero_lifeCycleSigma(1)']=xr.DataArray(oslo_aero_lifeCycleSigma_1, coords={'nmb_sim':np.arange(nmb_sim)})
out_ds['oslo_aero_lifeCycleSigma(8)']=xr.DataArray(oslo_aero_lifeCycleSigma_8, coords={'nmb_sim':np.arange(nmb_sim)})
out_ds['oslo_aero_lifeCycleNumberMedianRadius(1)']=xr.DataArray(oslo_aero_lifecyclenumbermedianradius_1, coords={'nmb_sim':np.arange(nmb_sim)})
out_ds['oslo_aero_lifeCycleNumberMedianRadius(8)']=xr.DataArray(oslo_aero_lifecyclenumbermedianradius_8, coords={'nmb_sim':np.arange(nmb_sim)})
# Save the dataset to a NetCDF file
out_ds.to_netcdf("NorESM_testParams_001_31.nc")

# %%