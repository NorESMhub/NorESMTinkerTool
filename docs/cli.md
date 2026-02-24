# Commandline interface (CLI)

This section describes the CLI of NorESMTinkerTool.
The CLI contains two main programs:

- `generate-paramfile`: Generate parameter file for PPE. 
- `create-ppe`: Create PPE experiment.

There is also a specific script meant for the `aerosol_ppe`.  


!!! warning Prerequisites
    Before the package can be used, the path to the NorESM directory must be set, by specifying the `CESMROOT` environmental variable, such that it can find the required CIME libraries.

    ```
    export CESMROOT=/path/to/NorESM
    ```

The CLI also requires that `simulation_setup.ini` file is created, see [Base Configuration of PPE runs](configuration.md) for more information.

The package then has the following use cases:

1. Generate parameter file for PPE.
2. Creates the PPE.

The CLI exposes the same options as API/ scripting method. is detailed further in the following subsections. Therefore, refer to API documentation for more information on what each of the option do. 

A description of the functionalities of the CLI tool is found by running `generate-paramfile --help`:
```bash
usage: generate-paramfile [-h] [--verbose VERBOSE] [--log-dir LOG_DIR] [--log-mode LOG_MODE] --param-ranges-inpath PARAM_RANGES_INPATH --param-sample-outpath PARAM_SAMPLE_OUTPATH [--nmb-sim NMB_SIM] [--method METHOD] [--chem-mech-file CHEM_MECH_FILE]
                          [--ctsm-default-param-file CTSM_DEFAULT_PARAM_FILE] [--fates-default-param-file FATES_DEFAULT_PARAM_FILE] [--tinkertool-output-dir TINKERTOOL_OUTPUT_DIR] [--optimization OPTIMIZATION] [--avoid-scramble]
                          [--params PARAMS [PARAMS ...]] [--exclude-default] [--version]

Parameter file generation configuration.

options:
  -h, --help            show this help message and exit
  --verbose VERBOSE     Increase verbosity level (0: WARNING, 1: INFO, 2: INFO_DETAILED, 3: DEBUG)
  --log-dir LOG_DIR     Path to the log directory where logs will be written. If not specified, logs will be printed in current work directory.
  --log-mode LOG_MODE   Mode for opening the log file ('w' for write, 'a' for append, 'o' for no logging, default: 'w')
  --param-ranges-inpath PARAM_RANGES_INPATH
                        Path to the parameter ranges file in .ini format
  --param-sample-outpath PARAM_SAMPLE_OUTPATH
                        Path to the output parameter file with .nc extension
  --nmb-sim NMB_SIM     Number of ensemble members. (required for latin_hypercube, should not be specified for one_at_a_time)
  --method METHOD       Sampling method, valid options: latin_hypercube (lh), one_at_a_time (oat). Default is latin_hypercube.
  --chem-mech-file CHEM_MECH_FILE
                        Path to the chemistry mechanism file, default None will not modify chemistry mechanism.
  --ctsm-default-param-file CTSM_DEFAULT_PARAM_FILE
                        Path to the default CTSM parameter file in netCDF format, default None will not modify CTSM parameters
  --fates-default-param-file FATES_DEFAULT_PARAM_FILE
                        Path to the default FATES parameter file in netCDF format, default None will not modify FATES parameters
  --tinkertool-output-dir TINKERTOOL_OUTPUT_DIR
                        Path to the output directory for files produced by TinkerTool, default will use NorESMTinkerTool/output (default: None)
  --optimization OPTIMIZATION
                        Whether to enable optimization after sampling, valid random-cd or lloyd. Default None.
  --avoid-scramble      Overwrite the default scramble of hypercube, i.e. scramble=False to center samples within cells of a multi-dimensional grid. If it is not called, samples are randomly placed within cells of the grid. (default: False)
  --params PARAMS [PARAMS ...]
                        List of parameters to be sampled, have to be defined in param_ranges_inpath. If unspecified all parameters in param_ranges_inpath will be used
  --exclude-default     Whether to exclude the default parameter value in the output file in nmb_sim=0. Using this flag will skip nmb_sim=0. Default is to include default value. (default: False)
  --version, -v         show program's version number and exit

```

Similarly for the `create-ppe` program:

```bash
usage: create-ppe [-h] [--verbose VERBOSE] [--log-dir LOG_DIR] [--log-mode LOG_MODE] --simulation-setup-path SIMULATION_SETUP_PATH [--build-base-only] [--build-only] [--frozen-base-case] [--keepexe] [--overwrite-base-case] [--overwrite-ppe] [--version]

CreatePPEConfig(verbose: int = 0, log_dir: pathlib._local.Path | str = '', log_mode: str = 'w', *, simulation_setup_path: pathlib._local.Path, build_base_only: bool = False, build_only: bool = False, frozen_base_case: bool = False, keepexe: bool =
False, overwrite_base_case: bool = False, overwrite_ppe: bool = True)

options:
  -h, --help            show this help message and exit
  --verbose VERBOSE     Increase verbosity level (0: WARNING, 1: INFO, 2: INFO_DETAILED, 3: DEBUG)
  --log-dir LOG_DIR     Path to the log directory where logs will be written. If not specified, logs will be printed in current work directory.
  --log-mode LOG_MODE   Mode for opening the log file ('w' for write, 'a' for append, 'o' for no logging, default: 'w')
  --simulation-setup-path SIMULATION_SETUP_PATH
                        Path to user defined configuration file for simulation setup.
  --build-base-only     Only build the base case - not PPE members (default: False)
  --build-only          Only build the PPE and not submit them to the queue (default: False)
  --frozen-base-case    Only clone the base case and not build the PPE members. This is useful if you have already built the base_case. (default: False)
  --keepexe             Reuse the executable for the base case instead of building a new one for each member (default: False)
  --overwrite-base-case
                        Overwrite the existing base case it it exists, e.g. it will rebuild the entire case from scratch, required if code changes are made. (default: False)
  --overwrite-ppe       Overwrite PPE ensemble cases if they exist (default: False)
  --version, -v         show program's version number and exit

```
