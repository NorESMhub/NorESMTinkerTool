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

Note that the package requires python >=3.10,<3.12 to be active in your enviroment.

2. clone repository:
```
git clone git@github.com:Johannesfjeldsaa/NorESMTinkerTool.git && cd NorESMTinkerTool
```

You are now in `<tinkerroot>`.

3. Install

```
pip install -e  ./
```
Or, to include optionals:
```
pip install -e  .[optional1, ..., optionalx]
```
Available optionals:

* sampling

Note that the `-e` puts the package in editable mode, if it is not included changes to configuration files etc will not be available before you re install the package.

## Repository description

### default_config

The purpose of this directory is to hold files that are general purpose for different PPE's within a model version. Current content:

* `default_config/default_param_ranges.ini` - Default parameter ranges for tunable parameters. This serves as a work-in-progress database for tuning parameters. See the in-file description for how to use and contribute.
* `default_config/chem_mech_default.in` - Copy of the `chem_mech.in` file used in CAM to generate the chemistry code. Standard location of original is `NorESM/components/cam/src/chemistry/pp_trop_mam_oslo/chem_mech.in`. This copy is needed if you want to do tuning that touches the cemical reactions. **Note:** current implementation of `generate-paramfile` only support changes to SOA_y_scale.

## Usage

Before the package can be used, the path to the NorESM directory must be set, by specifying the `CESMROOT` enviromental variable, such that it can find the required CIME libraries.

```
export CESMROOT=/path/to/NorESM
```

The package then has the following use cases:

1. Generate parameter file for PPE.
2. Create PPE.
    - build ensemble members
    - check build
    - prestage data
    - submit ppe to queue

Package usage is detailed further in the following subsections.

### Generate parameter file for PPE

To generate the parameter file for the ppe we use `generate-paramfile` program.
Requirements:
* scipy and xarray should be installed, ensure optional 'sampling' is included in installation command `pip install -e .[sampling]`.
* Update input files:
  * Update parameter ranges by either adding/editing entries in `default_config/default_param_ranges.ini` or by feeding an updated custom path to --param-ranges-file (see more information bellow).
  * `default_config/chem_mech_default.in` should be renewed if you are perterbing values from `NorESM/components/cam/src/chemistry/pp_trop_mam_oslo/`.

The script generates a netCDF file containing a Latin Hypercube sample of parameters for a PPE experiment. The .nc file will have one dimension, 'nmb_sim', which contains the number of ensemble members. Each parameter is stored as a variable in the dataset and is scaled according to its specified range and sampling method.

There are two options for creating a parameterfile after installation:

* A command line interface (CLI) callable from <tinkerroot>. Running
```bash
generate-paramfile --help
usage: generate-paramfile [-h] [--chem-mech-file CHEM_MECH_FILE] [--tinkertool-output-dir TINKERTOOL_OUTPUT_DIR] [--nmb-sim NMB_SIM] [--optimization OPTIMIZATION] [--avoid-scramble] [--params PARAMS [PARAMS ...]] [--assumed-esm-component ASSUMED_ESM_COMPONENT] [--exclude-default] [--verbose]
                          [--log-file LOG_FILE] [--log-mode LOG_MODE]
                          param_ranges_inpath param_sample_outpath

Generates a Latin Hyper Cube parameter file for PPE experiment

positional arguments:
  param_ranges_inpath   Path to the parameter ranges file in .ini format, default ranges are found in NorESMTinkerTool/default_config/default_param_ranges.ini
  param_sample_outpath  Path to the output parameter file with .nc extension.

options:
  -h, --help            show this help message and exit
  --chem-mech-file CHEM_MECH_FILE, -cmf CHEM_MECH_FILE
                        Path to the chemistry mechanism file, default None will use NorESMTinkerTool/default_config/default_chem_mech.in
  --tinkertool-output-dir TINKERTOOL_OUTPUT_DIR, -tod TINKERTOOL_OUTPUT_DIR
                        Path to the output directory for files produced by TinkerTool, default None will use NorESMTinkerTool/output
  --nmb-sim NMB_SIM, -ns NMB_SIM
                        Number of ensemble members, default 30
  --optimization OPTIMIZATION, -opt OPTIMIZATION
                        Whether to enable optimazation after sampling, valid random-cd or lloyd. Default None.
  --avoid-scramble, -asc
                        Overwrite the default scramble of hypercube, i.e. scramble=False to center samples within cells of a multi-dimensional grid. If it is not called, samples are randomly placed within cells of the grid.
  --params PARAMS [PARAMS ...], -p PARAMS [PARAMS ...]
                        List of parameters to be sampled, have to be defined in param_ranges_inpath. If unspecified all parameters in param_ranges_inpath will be used
  --assumed-esm-component ASSUMED_ESM_COMPONENT, -ac ASSUMED_ESM_COMPONENT
                        Assume component for parameter. This is used if component is not specified for an entry in the parameter ranges file. Default is 'cam'.
  --exclude-default, -exd
                        Whether to exclude the default parameter value in the output file in nmb_sim=0. Using this flag will skip nmb_sim=0. Default is to include default value.
  --verbose, -v         Increase verbosity level by number of v's (0: WARNING, 1: INFO, 2: INFO_DETAILED, 3: DEBUG)
  --log-file LOG_FILE, -l LOG_FILE
                        Path to the log file where logs will be written. If None, logs will not be saved to a file.
  --log-mode LOG_MODE, -lm LOG_MODE
                        Mode for opening the log file. 'w' for write (overwrite), 'a' for append. Default is 'w'.
```
will give you a discription of expected input.

* A importable function if you prefer running from another script. The main function only takes a ParameterFileConfig object as input. Basic usage:
```python
from pathlib import Path
from tinkertool.scripts.generate_paramfile.config import ParameterFileConfig
from tinkertool.scripts.generate_paramfile.generate_paramfile import generate_paramfile

parmfile_config = ParameterFileConfig(
  param_ranges_inpath=Path(<param_ranges.ini>).resolve(),
  param_sample_outpath=Path(<param_samples.nc>).resolve(),
  chem_mech_file=Path(<NorESMTinkerTool/default_config/default_chem_mech.in>).resolve(),
  tinkertool_output_dir=Path(<NorESMTinkerTool/output>).resolve(),
  nmb_sim=30,
  optimization=None,
  avoid_scramble=False,
  params=None,
  assumed_esm_component='cam',
  exclude_default=False,
  verbose=0,
  log_file=None,
  log_mode='w'
)
```

Common for both the CLI and scripting is that you will have to provide the same arguments. See the `generate_paramfile --help` print above for details. For `param_ranges_inpath` the expected format used by the script is:
```ini
[parameter_name]
component = <component name (used to assign the parameter to a component namelist file)>
description = <short description of the parameter>
justification = <justification for sampling range>
min = <lower bound for sampling>
max = <upper bound for sampling>
default = <default value for the parameter in the model version>
ndigits = <number of digits to use in sampling, i.e. sampling resolution>
sampling = <linear/log> (linear or log_10 scale sampling)
```

If you find a tabular format more easy to work with it is possible to convert from `.csv` to `.ini` using

```python
import pandas as pd
from pathlib import Path
from tinkertool.utils.csv_to_ini import df_to_ini

df = pd.read_csv(<input_csv_file>)

df_to_ini(
    df=df,
    ini_file_path=Path(<output path for .ini file>).resolve(),
    section_column=<column with section header (parameter name)>
    columns_to_include=<names of columns that should be used as keys in .ini>
)
```

see `tinkertool/utils/csv_to_ini.py` for more documentation on `df_to_ini` function.

### Create PPE

To Create the PPE we use `create-ppe` program. This uses only the libraries provided by the basic installation.

There are two options for creating a ppe after installing tinkertool:
* A command line interface (CLI) callable from `<tinkerroot>`. Running
```sh
python main.py --help
usage: main.py [-h] [--build-base-only] [--build-only] [--keepexe] [--overwrite] [-v] simulation_setup_path

Build PPE cases for NorESM

positional arguments:
  simulation_setup_path
                        Path to user defined configuration file for simulation setup.

options:
  -h, --help            show this help message and exit
  --build-base-only     Only build the base case - not PPE members
  --build-only          Only build the PPE and not submit them to the queue
  --keepexe, -k         Reuse the executable for the base case instead of building a new one for each member
  --overwrite, -o       Overwrite existing cases if they exist
  -v, --verbose         Increase verbosity level (0: WARNING, 1: INFO, 2: DEBUG)
```
will give you a discription of excpected inputs.
* A importable function if you prefer running from another script. The main function only takes a CreatePPEConfig object as input. Basic usage
```python
from pathlib import Path
from tinkertool.scripts.crate_ppe.config import CreatePPEConfig
from tinkertool.scripts.create_ppe.create_ppe import create_ppe

# describe the expected input to PPEConfig
CreatePPEConfig.describe()

ppe_config = CreatePPEConfig(
  simulation_setup_path = Path(<simulation_setup.ini>).resolve(),
  build_base_only       = False,
  build_only            = False,
  keepexe               = False,
  overwrite             = False,
  verbose               = 0,
  log_file              = Path(<wanted_logfile.out>).resolve(),
  log_mode              = 'w'
)

create_ppe(ppe_config)
```
alternatively if you only want to either a) build or b) submit cases use
```python
from pathlib import Path
from tinkertool.scripts.crate_ppe.config import BuildPPEConfig, SubmitPPEConfig
from tinkertool.scripts.create_ppe.create_ppe import build_ppe, submit_ppe

# a) Build only
BuildPPEConfig.help()
buildppe_config = BuildPPEConfig(
  simulation_setup_path = Path(<simulation_setup.ini>).resolve(),
  build_base_only       = False,
  keepexe               = False,
  overwrite             = False,
  verbose               = 0,
  log_file              = Path(<wanted_logfile.out>).resolve(),
  log_mode              = 'w'
)
build_ppe(buildppe_config)

# b) Sumbit only
SubmitPPEConfig.help()
submitppe_config = SubmitPPEConfig(
  cases                 = list(Path(<case1>).resolve(), ..., Path(<caseX>).resolve())
  verbose               = 0,
  log_file              = Path(<wanted_logfile.out>).resolve(),
  log_mode              = 'w'
)

submit_ppe(submitppe_config)
```

Common for both the CLI and scripting is that you will have to provide the same arguments. All input is self explanatory what to pass except the `simulation_setup.ini` file which you provide to 'simulation_setup_path' and which have to follow a specific template:

#### simulation_setup.ini

The simulation setup is expected to be a `.ini` file which must contain extensive information on the PPE cases. Current setup uses the following sections; `create_case`, `env_run`, `env_build`, `ppe_settings`, `namelist_control` and `lifeCycleValues`.

**crate_case** - This section holds key-value pairs used for creating a new case, i.e. what one does when running `./cime/scripts/create_newcase <args>`. *Required* keys are `cesmroot`, `res`, `compset_name`, `project`, `mach`, `walltime` and so a valid section will consist of:
```ini
[create_case]
cesmroot   = <absolute path to NorESM>
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
CALENDAR  = <calendar type>
```

It is possible to use additional key-value pairs in this section as well. As key-value pairs are given to `Case.set_value()` (where `Case` is an object defined from `NorESM/cime/CIME/case/case.py`) available/unused are available by running `./xmlquery --listall` in a case directory. To see information for a key run `./xmlquery <key> --full`. **NOTE**: Additional key-value pairs to those already discussed are attempted set using a loop over remaining pairs, a warning is raised if it is not successfull but program will not exit. This is done *after* the handling of the other keys.

**ppe_settings** - This section holds key-value paris used for pointing to the parameter file previously discussed and ensuring correct case paths for PPE members. *Required* keys are `paramfile`, `pdim`, `baseroot`, `basecasename`, `basecase_id` and `assumed_esm_component`. A valid section is therefore:

```ini
paramfile             = <absolute path to .nc parameter samples>
pdim                  = <ensemlbe number dimension name in paramfile>
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
control_cam = <path to control_cam.ini or None (example in input_file_templates/template_control_atm.ini)>
control_clm = <path to control_clm.ini or None(example in input_file_templates/template_control_clm.ini)>
```

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

**NOTE**: You do not need to add the name of the parameters you are pertermbing to these .ini files.
