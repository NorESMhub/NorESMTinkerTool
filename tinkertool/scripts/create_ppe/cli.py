import argparse
from pathlib import Path

from tinkertool.scripts.create_ppe.config import CreatePPEConfig


def parse_cli_args() -> CreatePPEConfig:
    parser = argparse.ArgumentParser(description="Build PPE cases for NorESM")
    parser.add_argument(
        "simulation_setup_path",
        type=str,
        help="Path to user defined configuration file for simulation setup.",
    )
    parser.add_argument(
        "--build-base-only",
        "-bbo",
        action="store_true",
        help="Only build the base case - not PPE members",
    )
    parser.add_argument(
        "--build-only",
        "-bo",
        action="store_true",
        help="Only build the PPE and not submit them to the queue",
    )
    parser.add_argument(
        "--clone_only_during_build",
        "-codb",
        action="store_true",
        help="Only clone the base case during build, skip build of base case. This is useful if you have already buildt the base case.",
    )
    parser.add_argument(
        "--keepexe",
        "-k",
        action="store_true",
        help="Reuse the executable for the base case instead of building a new one for each member",
    )
    parser.add_argument(
        "--overwrite",
        "-o",
        action="store_true",
        help="Overwrite existing cases if they exist",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        type=int,
        default=0,
        action="count",
        help="Increase verbosity level by number of v's (0: WARNING, 1: INFO, 2: INFO_DETAILED, 3: DEBUG)",
    )
    parser.add_argument(
        "--log-file",
        "-l",
        type=str,
        default=None,
        help="Path to the log file where logs will be written. If None, logs will not be saved to a file.",
    )
    parser.add_argument(
        "--log-mode",
        "-lm",
        type=str,
        default="w",
        help="Mode for opening the log file. 'w' for write (overwrite), 'a' for append. Default is 'w'.",
    )

    args = parser.parse_args()
    return CreatePPEConfig(
        simulation_setup_path=Path(args.simulation_setup_path).resolve(),
        build_base_only=args.build_base_only,
        build_only=args.build_only,
        clone_only_during_build=args.clone_only_during_build,
        keepexe=args.keepexe,
        overwrite=args.overwrite,
        verbose=args.verbose,
        log_file=Path(args.log_file).resolve() if args.log_file else None,
        log_mode=args.log_mode,
    )
