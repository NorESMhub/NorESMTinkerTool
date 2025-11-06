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

The package then has the following use cases:

1. Generate parameter file for PPE.
2. Create PPE.

Package usage is detailed further in the following subsections.


## Generate parameter file for PPE

To generate the parameter file for the PPE we use `generate-paramfile` program.

Requirements:

- scipy and xarray should be installed, ensure optional 'sampling' is included in installation command `pip install -e .[sampling]`.
- Update input files:
- Update parameter ranges by either adding/editing entries in `default_config/default_param_ranges.ini` or by feeding an updated custom path to --param-ranges-file (see more information bellow).
- `default_config/chem_mech_default.in` should be renewed if you are perturbing values from `NorESM/components/cam/src/chemistry/pp_trop_mam_oslo/`.

To generate the parameter file for the PPE we use Latin Hypercube sampling 
to most efficiently span the whole parameter space. 
The product of the script is a .nc file that will have one dimension, 
'nmb_sim', which contains the number of ensemble members. Each parameter is 
stored as a variable in the dataset and is scaled according to its 
specified range and sampling method. The ranges as described in the
`default_config/default_param_ranges.ini` file are used to distribute
parameter values between its minimum and maximum bounds.


A importable function if you prefer running from another script. The main function only takes a CreatePPEConfig object as input. Basic example
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