import argparse
from pathlib import Path
from tinkertool.scripts.generate_paramfile.config import ParameterFileConfig

def parse_cli_args() -> ParameterFileConfig:
    # --- Define CLI arguments
    parser = argparse.ArgumentParser(
        description="Generates a Latin Hyper Cube parameter file for PPE experiment")
    parser.add_argument("param_ranges_inpath", type=str,
        help="Path to the parameter ranges file in .ini format, default ranges are found in NorESMTinkerTool/default_config/default_param_ranges.ini")
    parser.add_argument("param_sample_outpath", type=str,
        help="Path to the output parameter file with .nc extension.")
    parser.add_argument("--chem-mech-file", "-cmf", type=str, default=None,
        help="Path to the chemistry mechanism file, default None will use NorESMTinkerTool/default_config/default_chem_mech.in")
    parser.add_argument("--tinkertool-output-dir", "-tod", type=str, default=None,
        help="Path to the output directory for files produced by TinkerTool, default None will use NorESMTinkerTool/output")
    parser.add_argument("--nmb-sim", '-ns', type=int, default=30,
        help="Number of ensemble members, default 30")
    parser.add_argument("--optimization", "-opt", type=str, default=None,
        help="Whether to enable optimazation after sampling, valid random-cd or lloyd. Default None.")
    parser.add_argument("--avoid-scramble", "-asc", action="store_true",
        help="Overwrite the default scramble of hypercube, i.e. scramble=False to center samples within cells of a multi-dimensional grid. If it is not called, samples are randomly placed within cells of the grid.")
    parser.add_argument("--params", "-p", nargs="+", type=str,
        help="List of parameters to be sampled, have to be defined in param_ranges_inpath. If unspecified all parameters in param_ranges_inpath will be used")
    parser.add_argument("--exclude-default", "-exd", action="store_true",
        help="Whether to exclude the default parameter value in the output file in nmb_sim=0. Using this flag will skip nmb_sim=0. Default is to include default value.")
    parser.add_argument("--verbose", "-v", default=0, action="count",
        help="Increase verbosity level by number of v's (0: WARNING, 1: INFO, 2: INFO_DETAILED, 3: DEBUG)")
    parser.add_argument("--log-dir", "-ld", type=str, default=None,
        help="Path to the log directory where logs will be written. If None, logs will be written to current work directory.")
    parser.add_argument("--log-mode", "-lm", type=str, default="w",
        help="Mode for opening the log file. 'w' for write (overwrite), 'a' for append. Default is 'w'.")


    args = parser.parse_args()

    return ParameterFileConfig(
        param_ranges_inpath=Path(args.param_ranges_inpath).resolve(),
        param_sample_outpath=Path(args.param_sample_outpath).resolve(),
        chem_mech_file=Path(args.chem_mech_file).resolve() if args.chem_mech_file else None,
        tinkertool_output_dir=Path(args.tinkertool_output_dir).resolve() if args.tinkertool_output_dir else None,
        nmb_sim=args.nmb_sim,
        optimization=args.optimization,
        avoid_scramble=args.avoid_scramble,
        params=args.params,
        exclude_default=args.exclude_default,
        verbose=args.verbose,
        log_dir=Path(args.log_dir).resolve() if args.log_dir else None,
        log_mode=args.log_mode
    )