# API Usage
This section describes how to use the NorESMTinkerTool package, within a python script using the internal API.

## 📚 Contents
- [Prerequisites](#prerequisites)
- [Generate parameter file for PPE](#generate-parameter-file-for-ppe)
- [Create PPE](#create-ppe)

## 📣 Prerequisites

Before the package can be used, the path to the NorESM directory must be set, by specifying the `CESMROOT` enviromental variable, such that it can find the required CIME libraries.

```bash
export CESMROOT=/path/to/NorESM
```

## Generate the PPE parameter file 

To generate the parameter file for the PPE we use `generate_paramfile` program. If you would like to use the CLI have a look under the CLI documentation. Below we will describe how to use API in a stand alone python script.

!!! note Prerequisites 
    - scipy and xarray should be installed, ensure optional 'sampling' is included in installation command `pip install -e .[sampling]`.
    - Update input files:
    - Update parameter ranges by either adding/editing entries in `default_config/default_param_ranges.ini` or by feeding an updated custom path to --param-ranges-file (see more information bellow).
    - `default_config/chem_mech_default.in` should be renewed if you are perturbing values from `NorESM/components/cam/src/chemistry/pp_trop_mam_oslo/`.

The parameter file is created using Latin Hypercube sampling 
to most efficiently span the whole parameter space. 
The outcome the script is a .nc file that will have one dimension, 
'nmb_sim', which contains the number of ensemble members. Each parameter is 
stored as a variable in the dataset and is scaled according to its 
specified range and sampling method. The ranges as described in the
`default_config/default_param_ranges.ini` file are used to distribute
parameter values between its minimum and maximum bounds.

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
description = <short description of the parameter>
justification = <justification for sampling range>
min = <lower bound for sampling>
max = <upper bound for sampling>
default = <default value for the parameter in the model version>
ndigits = <number of digits to use in sampling, i.e. sampling resolution>
sampling = <linear/log> (linear or log_10 scale sampling)
format_to_file_method = <f-string, if you want to use f-string to specify parameter values>
esm_component = <Which component of the model this parameter belongs to e.g. CAM>
```

## Create the PPE
```python
The main function only takes a CreatePPEConfig object as input. Basic usage
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
Alternatively if you only want to either a) build or b) submit cases use

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

The `simulation_setup.ini` file is described in detail [configuration](configuration.md).