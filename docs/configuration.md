
# Configuring the BaseCase for the PPE
The interface of the API and CLI is generally straightforward in terms of what the arguments mean. 
The exception to this is the `simulation_setup.ini` file which is provided to 'simulation_setup_path' and which have to follow a specific template. 
The purpose of this file is to describe the BaseCase which will serve as the foundation for ensembles in 
the PPE. 
Where each ensemble of the PPE will share the same configuration as the BaseCase. 
The current setup uses the following sections; `create_case`, `env_run`, `env_build`, `ppe_settings`, `namelist_control` and `lifeCycleValues`.

## crate_case 
This section holds key-value pairs used for creating a new case, i.e. what one does when running `./cime/scripts/create_newcase <args>`. The minimum *required* keys are `cesmroot`, `res`, `compset_name`, `project`, `mach`, `walltime`. As shown in the example below. 

```ini
[create_case]
cesmroot   = <absolute path to NorESM>
res         = <long resolution name or alias>
compset     = <long compeset name or alias>
project     = <project name>
mach        = <machine name>
walltime    = <wall clock time per case>
```
!!! note  "Additional key-value pairs"
    Other common key-value pairs are given to `Case.create()` can be specified in addition to the required ones. 
    The available/unused key word arguments include `user_mods_dirs`, `pecount`, `compiler`, `mpilib`, 
    `pesfile`, `gridfile`, `multi_driver`, `ninst`, `test`, ` queue`, `output_root`, `input_dir`, `workflowid`, 
    `non_local`, `extra_machines_dir` and `case_group`. **Note**: Arguments `run_unsupported=True`, 
    `driver="mct"`, `answer="r"` are *"hard coded"* in `tinkertool.setup.case.build_base_case()` and is therefor 
    not available. We refer to the CIME source code for proper usage of the available/unused key word arguments.


## env_run and env_build 
This section holds key-value pairs used for setting environmental variables for the model, i.e. the equivalent 
functionality to using `./xmlchange` in a case directory. 
The minimum *required* keys are `RUN_TYPE`, `STOP_OPTION`, `STOP_N` and `RUN__STARTDATE`. 
In addition this implementation has explicit handling off `GET_REFCASE`, `RUN_REFCASE`, `RUN_REFDIR`, 
`RUN_REFDATE`, `REST_OPTION`, `REST_N` for *env_run* and `CALENDAR`for *env_build*. 

!!! note "Changing CAM config" 
    To change `CAM_CONFIG_OPTS` there are two options; 1. provide a full and valid version of `CAM_CONFIG_OPTS`, 
    this will overwrite the default in full, or 2. provide `cam_onopts`, this will add the options to the 
    default. 
    
Below is an example of valid/recommended *env_run* and *env_build* section of `simulation_setup.ini`:

```ini
[env_run]
RUN_TYPE        = <type of run>
STOP_OPTION     = <measure of time to use for STOP_N>
STOP_N          = <count of the STOP_OPTION meassure to stop run at>
RUN_STARTDATE   = <date to start calendar in run>
; recomended entries for non-startup runs
GET_REFCASE     = <Flag for automatically prestaging the refcase restart dataset>
RUN_REFCASE     = <Reference case for hybrid or branch runs>
RUN_REFDIR      = <Reference directory containing RUN_REFCASE data>
RUN_REFDATE     = <Reference date for hybrid or branch runs (yyyy-mm-dd)>
REST_OPTION     = <measure for frequency of model restart writes>
REST_N          = <count of the REST_OPTION meassure>
; specially handled keys
CAM_CONFIG_OPTS = <replacement to existing CAM_CONFIG_OPTS>
; OR
cam_onopts      = <string to add to existing CAM_CONFIG_OPTS>

[env_build]
CALENDAR  = <calendar type>
```
It is possible to use additional key-value pairs in this section as well. As key-value pairs are given to `Case.set_value()` (where `Case` is an object defined from `NorESM/cime/CIME/case/case.py`).  Available pairs can be found by running `./xmlquery --listall` in a case directory. To see information for a key run `./xmlquery <key> --full`. 

!!! note Extra Key-values pairs 
    Additional key-value pairs to those already discussed are attempted set using a loop over remaining pairs, a warning is raised if it is not successful but the program will not exit. This is done *after* the handling of the other keys.

**ppe_settings** - This section holds key-value paris used for pointing to the parameter file create by the `generate_paramfile` function or `generate-paramfile`. This file is also used to specify the correct case paths for PPE members. *Required* keys are `paramfile`, `pdim`, `baseroot`, `basecasename`, `basecase_id` and `assumed_esm_component`. 
A template section below. 

```ini
paramfile             = <absolute path to .nc parameter samples>
pdim                  = <ensemble number dimension name in paramfile>
baseroot              = <absolute path to where you want ppe cases>
basecasename          = <name of basecase>
basecase_id           = <number used id-ing the basecase, e.g. 000 if we include default or 001 if we exclude it>
assumed_esm_component = <assumed component for variables in paramfile which dont have
                         'component' attribute. Used to send variable to the correct user_nl file >
```


## namelist_control 
- This section holds key-value pairs used for pointing to .ini files used to generate the user_nl_<component> which hold settings that are shared between all ensemble members. A valid section would be something like

```ini
[namelist_control]
control_atm = <path to control_atm.ini or None (example in input_file_templates/template_control_atm.ini)>
control_cpl = <path to control_cpl.ini or None (example in input_file_templates/template_control_cpl.ini)>
.... 
```

!!! warning 
    **NOTE:** The tinkertool uses the <component> part of `control_<component>.ini` to know which `user_nl_<component>` file to replace. Therefor use `control_<component>.ini` strictly for the filename.

If a `control_<component>` key is `= None` the model default one is used, otherwise the `.ini` file is used to create a string replacing user_nl_<component> via the follow ini-file syntax, e.g.:

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
Each section correspond to namelist group. Valid namelist variables are described in `namelist_definition*.xml` files:
* cam - `NorESM/components/cam/bld/namelist_files/namelist_definition.xml`
* clm - `NorESM/components/clm/bld/namelist_files/namelist_definition_ctsm.xml`

!!! note 
    You do not need to add the name of the parameters you are perturbing to these .ini files.

### f-string formating 

f-string formating offers a another way of for perturbing parameters in the namelists. This is done by putting a *f-string* placeholder that will be resolved with a parameter when building the PPE. The most common use case for this is to scale external forcing files. 
Below is an example how the *f-string* formatting looks. Here each placeholder with the same name will be filled with the same value during build. 

```
ext_frc_specifier = H2O    -> /cluster/shared/noresm/inputdata/atm/cam/chem/emis/elev/H2OemissionCH4oxidationx2_3D_L70_1849-2101_CMIP6ensAvg_SSP2-4.5_c190403.nc
	BC_AX  ->  {bc_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_BC_AX_airALL_vertical_1995-2025_1.9x2.5_version20250620.nc
	BC_AX  ->  {bc_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_BC_AX_anthroprofENEIND_vertical_1995-2025_1.9x2.5_version20250620.nc
	BC_N   ->  {bc_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_BC_N_airALL_vertical_1995-2025_1.9x2.5_version20250620.nc
	BC_N   ->  {bc_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_BC_N_anthroprofENEIND_vertical_1995-2025_1.9x2.5_version20250620.nc
	BC_NI  ->  {bc_scale_bio_specifer}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_BC_NI_bbAGRIBORFDEFOPEATSAVATEMF_vertical_1995-2025_1.9x2.5_version20250620.nc
	OM_NI  ->  {bc_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_OM_NI_airALL_vertical_1995-2025_1.9x2.5_version20250620.nc
	OM_NI  ->  {bc_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_OM_NI_anthroprofENEIND_vertical_1995-2025_1.9x2.5_version20250620.nc
	OM_NI  ->  {bc_scale_bio_specifer}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_OM_NI_bbAGRIBORFDEFOPEATSAVATEMF_vertical_1995-2025_1.9x2.5_version20250620.nc
	SO2    ->  {so2_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_SO2_airALL_vertical_1995-2025_1.9x2.5_version20250620.nc
	SO2    ->  {so2_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_SO2_anthroprofENEIND_vertical_1995-2025_1.9x2.5_version20250620.nc
	SO2    ->  /cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_SO2_bbAGRIBORFDEFOPEATSAVATEMF_vertical_1995-2025_1.9x2.5_version20250620.nc
	SO2    ->  {so2vul_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_SO2_volcCONTEXPL_vertical_1995-2025_1.9x2.5_version20250620.nc
	SO4_PR ->  {so2_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_SO4_PR_airALL_vertical_1995-2025_1.9x2.5_version20250620.nc
	SO4_PR ->  {so2_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_SO4_PR_anthroprofENEIND_vertical_1995-2025_1.9x2.5_version20250620.nc
	SO4_PR ->  /cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_SO4_PR_bbAGRIBORFDEFOPEATSAVATEMF_vertical_1995-2025_1.9x2.5_version20250620.nc
	SO4_PR ->  {so2vul_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_SO4_PR_volcCONTEXPL_vertical_1995-2025_1.9x2.5_version20250620.nc
srf_emis_specifier = BC_AX  ->  {bc_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_BC_AX_anthrosurfAGRTRADOMSOLWSTSHP_surface_1995-2025_1.9x2.5_version20250620.nc
	BC_N   ->  {bc_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_BC_N_anthrosurfAGRTRADOMSOLWSTSHP_surface_1995-2025_1.9x2.5_version20250620.nc
	OM_NI  ->  {bc_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_OM_NI_anthrosurfAGRTRADOMSOLWSTSHP_surface_1995-2025_1.9x2.5_version20250620.nc
	SO2    ->  {so2_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_SO2_anthrosurfAGRTRADOMSOLWSTSHP_surface_1995-2025_1.9x2.5_version20250620.nc
	SO4_PR ->  {so2_scale_specifier}*/cluster/shared/noresm/inputdata/atm/cam/chem/emis/cmip7_emissions_version20250620/emissions_cmip7_noresm3_SO4_PR_anthrosurfAGRTRADOMSOLWSTSHP_surface_1995-2025_1.9x2.5_version20250620.nc
```

!!! note 
    Parameters that should be provided as f-strings need be specified to use the f-string method using the following opition in the .ini file defining the parameters `format_to_file_method = f-string`.