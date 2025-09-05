
# Base Configuration of PPE runs
Before a PPE ensemble can be created, a base configuration of NorESM must specified. 
The arguments to pass in to the [CLI](cli.md) and [API](usage.md) is generally self explanatory, except for the `simulation_setup.ini` file which you provide to 'simulation_setup_path' and which have to follow a specific template.

This file contain extensive information on the base configuration of each of the PPE simulations. Each ensemble of the PPE will share the same configuration. Current setup uses the following sections; `create_case`, `env_run`, `env_build`, `ppe_settings`, `namelist_control` and `lifeCycleValues`.

**create_case** - This section holds key-value pairs used for creating a new case, i.e. what one does when running `./cime/scripts/create_newcase <args>`. *Required* keys are `cesm_root`, `res`, `compset_name`, `project`, `mach`, `walltime` and so a valid section will consist of:
```ini
[create_case]
cesm_root   = <absolute path to NorESM>
res         = <long resolution name or alias>
compset     = <long compeset name or alias>
project     = <project name>
mach        = <machine name>
walltime    = <wall clock time per case>
```
It is possible to use additional key-value pairs in this section as well. As key-value pairs are given to `Case.create()` (where `Case` is an object defined from `NorESM/cime/CIME/case/case.py`) available/unused key word arguments include `user_mods_dirs`, `pecount`, `compiler`, `mpilib`, `pesfile`, `gridfile`, `multi_driver`, `ninst`, `test`, ` queue`, `output_root`, `input_dir`, `workflowid`, `non_local`, `extra_machines_dir` and `case_group`. **Note**: Arguments `run_unsupported=True`, `driver="mct"`, `answer="r"` are *"hard coded"* in `tinkertool.setup.case.build_base_case()` and is therefor not available. We referr to the CIME source code for proper usage of the available/unused key word arguments.

**env_run** and **env_build** - This section holds key-value pairs used for setting enviromental variables for the model, i.e. what ones does when using `./xmlchange` in a case directory. *Required* keys are `RUN_TYPE`, `STOP_OPTION`, `STOP_N` and `RUN__STARTDATE`. In addition this implementation has explicit handling off `GET_REFCASE`, `RUN_REFCASE`, `RUN_REFDIR`, `RUN_REFDATE`, `REST_OPTION`, `REST_N` for *env_run* and `CALENDAR`for *env_build*. To change `CAM_CONFIG_OPTS` there are two options; 1. provide a full and valid version of `CAM_CONFIG_OPTS`, this will overwrite the default in full, or 2. provide `cam_onopts`, this will add the options to the default. A valid/recomended *env_run* and *env_build* section is then:

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
CALENDAR  = GREGORIAN
```

It is possible to use additional key-value pairs in this section as well. As key-value pairs are given to `Case.set_value()` (where `Case` is an object defined from `NorESM/cime/CIME/case/case.py`) available/unused are available by running `./xmlquery --listall` in a case directory. To see information for a key run `./xmlquery <key> --full`. **NOTE**: Additional key-value pairs to those already discussed are attempted set using a loop over remaining pairs, a warning is raised if it is not successfull but program will not exit. This is done *after* the handling of the other keys.

**ppe_settings** - This section holds key-value paris used for pointing to the parameter file previously discussed and ensuring correct case paths for PPE members. *Required* keys are `paramfile`, `pdim`, `baseroot`, `basecasename`, `basecase_id` and `assumed_esm_component`. A valid section is therefore:

```ini
paramfile             = <absolute path to .nc parameter samples>
pdim                  = <ensamlbe number dimension name in paramfile>
baseroot              = <absolute path to where you want ppe cases>
basecasename          = <name of basecase>
basecase_id           = <number used id-ing the basecase, e.g. 000 if we include default or 001 if we exclude it>
assumed_esm_component = <assumed component for variables in paramfile which dont have
                         'component' attribute. Used to send variable to the correct user_nl file >
```

Further key-value pairs is not implemented as of now.

**namelist_control** - This section holds key-value pairs used for pointing to .ini files used to generate custom user_nl_<component> files. A valid section would be something like

```ini
[namelist_control]
control_atm = <path to control_atm.ini or None (example in input_file_templates/template_control_atm.ini)>
control_cpl = <path to control_cpl.ini or None (example in input_file_templates/template_control_cpl.ini)>
control_cice = <path to control_cice.ini or None (example in input_file_templates/template_control_cice.ini)>
control_clm = <path to control_clm.ini or None(example in input_file_templates/template_control_clm.ini)>
control_docn = <path to control_docn.ini or None(example in input_file_templates/template_control_docn.ini)
```

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
* CAM - `NorESM/components/cam/bld/namelist_files/namelist_definition.xml`
* ...

**NOTE**: You do not need to add the name of the parameters you are pertermbing to these .ini files.