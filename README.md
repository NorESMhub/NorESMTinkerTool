# NorESMTinkerTool
_ A safe space for tinkering _ 

Python tool for setting up, running and analysing perturbed parameter ensembles with the Norwegian Earth System Model
(NorESM). 
By encuraging tinkering to greater extent we can better learn how the model works. 

## Installation 


1. Setup virtual eviroment.  

```
python3 -m venv tinkertool && source tinkertool/bin/activate
```

2. clone repository:
```
git clone https://github.com/Ovewh/NorESMTinkerTool.git && cd NorESMTinkerTool
```


3. Install 
```
pip install -e  ./
```

## Usage

Before the package can be used, the path to the NorESM directory must be set, by specifying the `CESMROOT` enviromental variable, such that it can find the required CIME libraries. 

```
export CESMROOT=/path/to/NorESM
```

Then it can be used as follows:

```
create-ppe --help
usage: create-ppe [-h] [--overwrite] [--pdim PDIM] [--config-setup CONFIG_SETUP] [--base-case-id BASE_CASE_ID] [--nl-cam NL_CAM] [--nl-cpl NL_CPL] [--nl-cice NL_CICE] [--nl-clm NL_CLM] [--nl-docn NL_DOCN]
                  [--build-base-only] [--cesm-root CESM_ROOT]
                  basecasename paramfile

Build PPE cases for NorESM

positional arguments:
  basecasename          Base case name
  paramfile             NetCDF file with PPE parameters

options:
  -h, --help            show this help message and exit
  --overwrite, -o       Overwrite existing cases
  --pdim PDIM           Name of dimension for number of simulations
  --config-setup CONFIG_SETUP, -cs CONFIG_SETUP
                        Path to user defined configuration file
  --base-case-id BASE_CASE_ID, -bci BASE_CASE_ID
                        Base case identifier
  --nl-cam NL_CAM, -cam NL_CAM
                        Path to user defined namelist file (CAM)
  --nl-cpl NL_CPL, -cpl NL_CPL
                        Path to user defined namelist file (CLP)
  --nl-cice NL_CICE, -cice NL_CICE
                        Path to user defined namelist file (CICE)
  --nl-clm NL_CLM, -ice NL_CLM
                        Path to user defined namelist file (CLM)
  --nl-docn NL_DOCN, -docn NL_DOCN
                        Path to user defined namelist file (DOCN)
  --build-base-only     Only build the base case
  --cesm-root CESM_ROOT, -cr CESM_ROOT
                        Path to CESM root directory, if not provided, will use CESMROOT environment variable
```

## Configuration
The `--nl-cam`, `--nl-cpl`, `--nl-cice`, `--nl-clm`, and `--nl-docn` options can be used to specify namelist files for the different components of the model. If not provided, the default namelist files will be used. The specification of the namelist files follow ini-file syntax, e.g.:

```
[metadata_nl]
met_data_file = /cluster/shared/noresm/inputdata/noresm-only/inputForNudging/ERA_f09f09_32L_days/2014-01-01.nc
met_filenames_list = /cluster/shared/noresm/inputdata/noresm-only/inputForNudging/ERA_f09f09_32L_days/fileList2001-2015.txt
met_nudge_only_uvps = .true.
met_nudge_temp = .false.
met_rlx_time = 6
met_srf_land = .false.

[cam_initfiles_nl]
bnd_topo=/cluster/shared/noresm/inputdata/noresm-only/inputForNudging/ERA_f09f09_32L_days/ERA_bnd_topo_noresm2_20191023.nc

[camexp]
empty_htapes = .true.
nhtfrq=0,-24
mfilt=1,30
cosp_passive=.true.
use_aerocom=.true.
history_aerosol=.true.
avgflag_pertape = A
fincl1 = AQRAIN
         AQSNOW
         AREI
         ACTREI
         ACTREL
         ACTNI
         ACTNL
         AWNC
         AWNI
         AIRMASS
         AIRMASSL
         ABS870
...
```
Each section correspond to namelist group.

## Creating the Parameter File

To create the PPE itself, requires a parameter file in NetCDF format. This have yet to be integrated into the package, but can be done manually. Currently a PPE can only be created of CAM parameters. Though should be easy to add more components in the future
```python
import xarray as xr
import numpy as np
import scipy.stats as stc

def scale_values(values, a, b):
    "Scale values from [0, 1] to [a, b] range"
    return a + (b - a) * values

# Create a hypercube for five parameters with 30 ensemble members
hypc = stc.qmc.LatinHypercube(5)
hyp_cube_parmas=hypc.random(30)

# Scale the values of the hypercube to be within the parameter ranges

scaled_emis_fact_in_cmod = scale_values(hyp_cube_parmas[:,0], 0.87,0.98)
dust_emis_fact_vals = scale_values(hyp_cube_parmas[:,1],0.2,1.2)
f_act_conv_coarse_dust_vals= scale_values(hyp_cube_parmas[:,2],.1, .9)
hetfrz_aer_scalfac_vals =  scale_values(hyp_cube_parmas[:,3],.001, .02)
microp_aero_wsub_min_vals = scale_values(hyp_cube_parmas[:,4], 0.001,0.3)

# Create xarray dataset with all the parameter combinations

out_ds = xr.Dataset(
    data_vars = dict(emis_fact_in_coarse_mode= (["nmb_sim"],scaled_emis_fact_in_cmod),
                    dust_emis_fact=(["nmb_sim"],dust_emis_fact_vals),
                    f_act_conv_coarse_dust=(["nmb_sim"],f_act_conv_coarse_dust_vals),
                    hetfrz_aer_scalfac=(["nmb_sim"],hetfrz_aer_scalfac_vals ), 
                    microp_aero_wsub_min= (["nmb_sim"],microp_aero_wsub_min_vals )),
                coords={'nmb_sim':np.arange(30)})

# Save the dataset to a NetCDF file
out_ds.to_netcdf("NorESM_testParams_001_30.nc")
```
