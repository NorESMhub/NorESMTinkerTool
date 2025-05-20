import logging
import configparser
import numpy as np
from pathlib import Path
from netCDF4 import Dataset
from typing import Union, Optional
from dataclasses import dataclass, fields, field, MISSING

from tinkertool.utils.read_files import read_config
from tinkertool.utils.logging import setup_logging
from tinkertool.setup.setup_cime_connection import add_CIME_paths_and_import
from tinkertool.utils.check_arguments import validate_file, validate_directory, check_type


@dataclass
class PPEConfig:
    """Base dataclass for PPE configuration."""
    verbose:    int = field(default=0, metadata={"help": "Increase verbosity level (0: WARNING, 1: INFO, 2: INFO_DETAILED, 3: DEBUG)"})
    log_file:   Path = field(default=None, metadata={"help": "Path to the log file where logs will be written. If None, logs will not be saved to a file."})
    log_mode:   str = field(default="w", metadata={"help": "Mode for opening the log file ('w' for write, 'a' for append)"})

    @classmethod
    def help(cls):
        print(f"Dataclass '{cls.__name__}' expects the following fields:")
        for inputfield in fields(cls):
            desc = inputfield.metadata.get("help", "")
            if inputfield.default is not MISSING:
                desc = f"{desc} (default: {inputfield.default!r})"
            else:
                desc = f"{desc} (required)"
            print(f"  {inputfield.name.ljust(25)}: {str(inputfield.type).ljust(25)} {desc}")

    def describe(self, return_string: bool = True):
        lines = [f"Instance of dataclass '{self.__class__.__name__}' has the following values:"]
        for inputfield in fields(self):
            desc = inputfield.metadata.get("help", "")
            value = getattr(self, inputfield.name)
            lines.append(f"  {inputfield.name.ljust(25)}: {str(inputfield.type).ljust(25)} = {value!r}  {desc}")
        if return_string:
            return "\n".join(lines)
        else:
            print("\n".join(lines))

    def check_and_handle_arguments(self):
        """Check and handle arguments for the PPE configuration."""
        # verbose
        if self.verbose not in [0, 1, 2, 3]:
            raise ValueError(f"Invalid verbosity level: {self.verbose}. Must be 0, 1, 2, or 3.")
        # log_mode
        if self.log_mode not in ["w", "a"]:
            raise ValueError(f"Invalid log mode: {self.log_mode}. Must be 'w' or 'a'.")
        if not logging.getLogger().hasHandlers():
            setup_logging(self.verbose, self.log_file, self.log_mode)


@dataclass
class CreatePPEConfig(PPEConfig):
    # will have the same fields as PPEConfig, but with additional fields:
    simulation_setup_path:  Path = field(default=None, metadata={"help": "Path to user defined configuration file for simulation setup."})
    build_base_only:        bool = field(default=False, metadata={"help": "Only build the base case - not PPE members"})
    build_only:             bool = field(default=False, metadata={"help": "Only build the PPE and not submit them to the queue"})
    keepexe:                bool = field(default=False, metadata={"help": "Reuse the executable for the base case instead of building a new one for each member"})
    overwrite:              bool = field(default=False, metadata={"help": "Overwrite existing cases if they exist"})

    def __post_init__(self):
        # Check if the simulation_setup_path is provided
        if self.simulation_setup_path is None:
            raise ValueError("simulation_setup_path is required. Please provide a valid path to the simulation setup file.")

    def check_and_handle_arguments(self):
        """Check and handle arguments for the PPE configuration."""
        super().check_and_handle_arguments()

        # simulation_setup_path
        validate_file(self.simulation_setup_path, ".ini", "simulation setup file")
        # build_base_only
        check_type(self.build_base_only, bool)
        # build_only
        check_type(self.build_only, bool)
        # keepexe
        check_type(self.keepexe, bool)
        # overwrite
        check_type(self.overwrite, bool)
        # derived fields - we unpack the simulation setup file
        simulation_setup: configparser.ConfigParser = read_config(self.simulation_setup_path)
        # - ppe_settings
        baseroot = Path(simulation_setup['ppe_settings']['baseroot']).resolve()
        basecasename = simulation_setup['ppe_settings']['basecasename']
        basecase_id: str = simulation_setup['ppe_settings']['basecase_id']
        assumed_esm_component: str = simulation_setup['ppe_settings']['assumed_esm_component']
        ## - paramfile
        pdim: str = simulation_setup['ppe_settings']['pdim']
        paramfile_path: Path = Path(simulation_setup['ppe_settings']['paramfile']).resolve()
        validate_file(paramfile_path, ".nc", "paramfile")
        paramfile: Dataset = Dataset(paramfile_path, 'r')
        if pdim not in paramfile.dimensions.keys():
            raise SystemExit(f"ERROR: {pdim} is not a valid dimension in {paramfile_path}")
        paramdict: dict = paramfile.variables
        num_sims = paramfile.dimensions[pdim].size
        num_vars = len(paramfile.variables.keys())-1
        ensemble_num = paramfile[pdim]
        del paramdict[pdim]
        paramfile.close()
        # - namelist_control
        namelist_collection_dict = {}
        for control_nl in simulation_setup['namelist_control']:
            if control_nl is not None:
                control_nl = Path(control_nl).resolve()
                validate_file(control_nl, ".ini", f"namelist control file {control_nl.name}")
                namelist_collection_dict[control_nl.name] = read_config(control_nl)
            else:
                logging.warning(f"Control namelist is None for {control_nl.name}, using model default")
        # - create_case
        cesm_root = Path(simulation_setup['create_case']['cesm_root']).resolve()
        validate_directory(cesm_root, "CESM root directory")
        add_CIME_paths_and_import(cesm_root)

        return CheckedCreatePPEConfig(
            **self.__dict__,
            simulation_setup=simulation_setup,
            baseroot=baseroot,
            basecasename=basecasename,
            basecase_id=basecase_id,
            assumed_esm_component=assumed_esm_component,
            paramfile_path=paramfile_path,
            pdim=pdim,
            paramdict=paramdict,
            num_sims=num_sims,
            num_vars=num_vars,
            ensemble_num=ensemble_num,
            namelist_collection_dict=namelist_collection_dict,
            cesm_root=cesm_root
        )

@dataclass
class CheckedCreatePPEConfig(CreatePPEConfig):
    # Will have the same fields as CreatePPEConfig, but with additional fields:
    simulation_setup:       configparser.ConfigParser = field(metadata={"help": "Parsed simulation setup file"})
    # - ppe_settings
    baseroot:               Path = field(metadata={"help": "Path to the base case root directory"})
    basecasename:           str = field(metadata={"help": "Name of the base case"})
    basecase_id:            str = field(metadata={"help": "ID of the base case"})
    assumed_esm_component:  str = field(metadata={"help": "Assumed ESM component for entries that does not have a specified component attribute in paramfile"})
    # - paramfile
    paramfile_path:         Path = field(metadata={"help": "Path to the paramfile"})
    pdim:                   str = field(metadata={"help": "Dimension of ensamble member count in paramfile"})
    paramdict:              dict = field(metadata={"help": "Dictionary of parameters in the paramfile"})
    num_sims:               int = field(metadata={"help": "Number of ensemble members"})
    num_vars:               int = field(metadata={"help": "Number of variables in the paramfile"})
    ensemble_num:           np.ndarray = field(metadata={"help": "Ensemble number in the paramfile"})
    # - namelist_control
    namelist_collection_dict: dict = field(metadata={"help": "Dictionary of namelist parsed namelist_control files"})
    # - create_case
    cesm_root:              Path = field(metadata={"help": "Path to the CESM root directory"})

    def check_and_handle_arguments(self):
        logging.info(f"Checking and handling arguments for {self.__class__.__name__} is not needed.")

@dataclass
class BuildPPEConfig(CreatePPEConfig):
    # Override build_only: set as a dummy field, not used in BuildConfig
    build_only: Optional[bool] = field(
        default=None,
        metadata={"help": "Not used in BuildPPEConfig"}
    )

    def check_and_handle_arguments(self):
        # Run parent checks and get the checked config from CreatePPEConfig
        checked_create_ppe_config: CheckedCreatePPEConfig = super().check_and_handle_arguments()

        # delete the build_only field from the checked config
        for field in fields(checked_create_ppe_config):
            if field.name == "build_only":
                delattr(checked_create_ppe_config, field.name)

        return CheckedBuildPPEConfig(
            **checked_create_ppe_config.__dict__,
            build_only=self.build_only
        )

@dataclass
class CheckedBuildPPEConfig(CheckedCreatePPEConfig):
    # Override build_only: set as a dummy field, not used in BuildConfig
    build_only: Optional[bool] = field(
        default=None,
        metadata={"help": "Not used in CheckedBuildPPEConfig"}
    )

    def check_and_handle_arguments(self):
        logging.info(f"Checking and handling arguments for {self.__class__.__name__} is not needed.")

@dataclass
class SubmitPPEConfig(PPEConfig):
    cases:  Union[str, Path, list[str], list[Path]] = field(metadata={"help": "List of case directories to submit to the queue"})

    def check_and_handle_arguments(self):
        """Check and handle arguments for the PPE configuration."""
        super().check_and_handle_arguments()

        # cases
        if isinstance(self.cases, str):
            self.cases = [self.cases]
        elif isinstance(self.cases, Path):
            self.cases = [self.cases]
        elif isinstance(self.cases, list) and all(isinstance(case, str) or isinstance(case, Path) for case in self.cases):
            self.cases = [Path(case).resolve() for case in self.cases]
        else:
            raise ValueError(f"Invalid cases: {self.cases}. Must be a string, Path, or list of strings/Paths.")
        for case in self.cases:
            validate_directory(case, f"case directory {case.name}")

        return CheckedSubmitPPEConfig(**self.__dict__)

@dataclass
class CheckedSubmitPPEConfig(SubmitPPEConfig):
    # Will have the same fields as SubmitPPEConfig

    def check_and_handle_arguments(self):
        logging.info(f"Checking and handling arguments for {self.__class__.__name__} is not needed.")