# Usage

## 📚 Contents
- [Prerequisites](#prerequisites)
- [Generate parameter file for PPE](#generate-parameter-file-for-ppe)
- [Create PPE](#create-ppe)

## Prerequisites

Before the package can be used, the path to the NorESM directory must be set, by specifying the `CESMROOT` enviromental variable, such that it can find the required CIME libraries.

```
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
- `default_config/chem_mech_default.in` should be renewed if you are perterbing values from `NorESM/components/cam/src/chemistry/pp_trop_mam_oslo/`.

To generate the parameter file for the PPE we use Latin Hypercube sampling 
to most efficiently span the whole parameter space. 
The product of the script is a .nc file that will have one dimension, 
'nmb_sim', which contains the number of ensemble members. Each parameter is 
stored as a variable in the dataset and is scaled according to its 
specified range and sampling method. The ranges as described in the
`default_config/default_param_ranges.ini` file are used to distribute
parameter values between its minimum and maximum bounds.

There are two options for creating the parameterfile, (1) using the CLI tool:

### Command Line Interface (CLI)
This can 
```bash
usage: generate-paramfile [-h] [--chem-mech-file CHEM_MECH_FILE] [--tinkertool-output-dir TINKERTOOL_OUTPUT_DIR] [--nmb-sim NMB_SIM] [--optimization OPTIMIZATION] [--avoid-scramble]
                          [--params PARAMS [PARAMS ...]] [--assumed-esm-component ASSUMED_ESM_COMPONENT] [--exclude-default] [--verbose] [--log-file LOG_FILE] [--log-mode LOG_MODE]
                          param_ranges_inpath param_sample_outpath

Generates a Latin Hyper Cube parameter file for PPE experiment

positional arguments:
  param_ranges_inpath   Path to the parameter ranges file in .ini format, default ranges are found in NorESMTinkerTool/default_config/default_param_ranges.ini
  param_sample_outpath  Path to the output parameter file with .nc extension.

options:
  -h, --help            show this help message and exit
  --chem-mech-file, -cmf CHEM_MECH_FILE
                        Path to the chemistry mechanism file, default None will use NorESMTinkerTool/default_config/default_chem_mech.in
  --tinkertool-output-dir, -tod TINKERTOOL_OUTPUT_DIR
                        Path to the output directory for files produced by TinkerTool, default None will use NorESMTinkerTool/output
  --nmb-sim, -ns NMB_SIM
                        Number of ensemble members, default 30
  --optimization, -opt OPTIMIZATION
                        Whether to enable optimazation after sampling, valid random-cd or lloyd. Default None.
  --avoid-scramble, -asc
                        Overwrite the default scramble of hypercube, i.e. scramble=False to center samples within cells of a multi-dimensional grid. If it is not called, samples are
                        randomly placed within cells of the grid.
  --params, -p PARAMS [PARAMS ...]
                        List of parameters to be sampled, have to be defined in param_ranges_inpath. If unspecified all parameters in param_ranges_inpath will be used
  --assumed-esm-component, -ac ASSUMED_ESM_COMPONENT
                        Assume component for parameter. This is used if component is not specified for an entry in the parameter ranges file. Default is 'cam'.
  --exclude-default, -exd
                        Whether to exclude the default parameter value in the output file in nmb_sim=0. Using this flag will skip nmb_sim=0. Default is to include default value.
  --verbose, -v         Increase verbosity level by number of v's (0: WARNING, 1: INFO, 2: INFO_DETAILED, 3: DEBUG)
  --log-file, -l LOG_FILE
                        Path to the log file where logs will be written. If None, logs will not be saved to a file.
  --log-mode, -lm LOG_MODE
                        Mode for opening the log file. 'w' for write (overwrite), 'a' for append. Default is 'w'.

```

The interal api can also be used to include `tinkertool` within a script. The main function only takes a ParameterFileConfig object as input. Basic usage
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
