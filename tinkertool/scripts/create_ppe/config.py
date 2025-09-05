import configparser
import logging
from dataclasses import MISSING, dataclass, field, fields
from pathlib import Path
from typing import Optional, Union

import numpy as np
from netCDF4 import Dataset

from tinkertool.setup.setup_cime_connection import add_CIME_paths_and_import
from tinkertool.utils.check_arguments import (
    check_type,
    validate_directory,
    validate_file,
)
from tinkertool.utils.read_files import read_config


def get_ncattr_or_default(var, attr, default=None):
    try:
        return var.getncattr(attr)
    except AttributeError:
        return default


@dataclass
class BaseConfig:
    """Base dataclass for parameter file generation configuration."""

    verbose: int = field(
        default=0,
        metadata={
            "help": "Increase verbosity level (0: WARNING, 1: INFO, 2: INFO_DETAILED, 3: DEBUG)"
        },
    )
    log_file: Path = field(
        default=None,
        metadata={
            "help": "Path to the log file where logs will be written. If None, logs will not be saved to a file."
        },
    )
    log_mode: str = field(
        default="w",
        metadata={
            "help": "Mode for opening the log file ('w' for write, 'a' for append)"
        },
    )

    def __post_init__(self):

        # check the arguments
        # verbose
        if self.verbose not in [0, 1, 2, 3]:
            raise ValueError(
                f"Invalid verbosity level: {self.verbose}. Must be 0, 1, 2, or 3."
            )
        # log_file
        if self.log_file is not None:
            if not self.log_file.exists():
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                self.log_file.touch()
        # log_mode
        if self.log_mode not in ["w", "a"]:
            raise ValueError(f"Invalid log mode: {self.log_mode}. Must be 'w' or 'a'.")

    @classmethod
    def help(cls):
        print(f"Dataclass '{cls.__name__}' expects the following fields:")
        for inputfield in fields(cls):
            desc = inputfield.metadata.get("help", "")
            if inputfield.default is not MISSING:
                desc = f"{desc} (default: {inputfield.default!r})"
            else:
                desc = f"{desc} (required)"
            print(
                f"  {inputfield.name.ljust(25)}: {str(inputfield.type).ljust(25)} {desc}"
            )

    def describe(self, return_string: bool = True):
        lines = [
            f"Instance of dataclass '{self.__class__.__name__}' has the following values:"
        ]
        for inputfield in fields(self):
            desc = inputfield.metadata.get("help", "")
            value = getattr(self, inputfield.name)
            lines.append(
                f"  {inputfield.name.ljust(25)}: {str(inputfield.type).ljust(25)} = {value!r}  {desc}"
            )
        if return_string:
            return "\n".join(lines)
        else:
            print("\n".join(lines))

    def get_checked_and_derived_config(self):
        pass


@dataclass
class CreatePPEConfig(BaseConfig):
    # will have the same fields as BaseConfig, but with additional fields:
    simulation_setup_path: Path = field(
        default=None,
        metadata={
            "help": "Path to user defined configuration file for simulation setup."
        },
    )
    build_base_only: bool = field(
        default=False, metadata={"help": "Only build the base case - not PPE members"}
    )
    build_only: bool = field(
        default=False,
        metadata={"help": "Only build the PPE and not submit them to the queue"},
    )
    clone_only_during_build: bool = field(
        default=False,
        metadata={
            "help": "Only clone the base case and not build the PPE members. This is useful if you have already built the base_case."
        },
    )
    keepexe: bool = field(
        default=False,
        metadata={
            "help": "Reuse the executable for the base case instead of building a new one for each member"
        },
    )
    overwrite: bool = field(
        default=False, metadata={"help": "Overwrite existing cases if they exist"}
    )

    def __post_init__(self):
        # run parent checks for the variables that are inherited from BaseConfig
        super().__post_init__()
        # check the arguments
        if self.simulation_setup_path is None:
            raise ValueError(
                "simulation_setup_path is required. Please provide a valid path to the simulation setup file."
            )
        validate_file(
            self.simulation_setup_path, ".ini", "simulation setup file", new_file=False
        )
        # build_base_only
        check_type(self.build_base_only, bool)
        # build_only
        # avoid checking if it is type BuildPPEConfig.
        # BuildPPEConfig overrides build_only as a dummy field
        if type(self) is CreatePPEConfig or type(self) is CheckedCreatePPEConfig:
            check_type(self.build_only, bool)
        # clone_only_during_build
        check_type(self.clone_only_during_build, bool)
        # keepexe
        check_type(self.keepexe, bool)
        # overwrite
        check_type(self.overwrite, bool)

    def get_checked_and_derived_config(self):
        """Check and handle arguments for the PPE configuration."""
        super().get_checked_and_derived_config()

        # derived fields - we unpack the simulation setup file
        simulation_setup: configparser.ConfigParser = read_config(
            self.simulation_setup_path
        )
        # - ppe_settings
        baseroot = Path(simulation_setup["ppe_settings"]["baseroot"]).resolve()
        basecasename = simulation_setup["ppe_settings"]["basecasename"]
        assumed_esm_component: str = simulation_setup["ppe_settings"][
            "assumed_esm_component"
        ]
        ## - paramfile
        pdim: str = simulation_setup["ppe_settings"]["pdim"]
        paramfile_path: Path = Path(
            simulation_setup["ppe_settings"]["paramfile"]
        ).resolve()
        validate_file(paramfile_path, ".nc", "paramfile", new_file=False)
        paramfile: Dataset = Dataset(paramfile_path, "r")
        if pdim not in list(paramfile.dimensions.keys()):
            raise SystemExit(
                f"ERROR: {pdim} is not a valid dimension in {paramfile_path}. \nParamfile dimensions are: {list(paramfile.dimensions.keys())}"
            )
        paramdict: dict = {k: v[:] for k, v in paramfile.variables.items() if k != pdim}
        componentdict: dict = {
            k: get_ncattr_or_default(v, "esm_component", assumed_esm_component)
            for k, v in paramdict.items()
        }
        num_sims = paramfile.dimensions[pdim].size
        num_vars = len(paramfile.variables.keys()) - 1
        ensemble_num = paramfile[pdim][:]
        paramfile.close()
        # - namelist_control
        namelist_collection_dict = {}
        for control_nl in simulation_setup["namelist_control"].values():
            if control_nl is not None:
                control_nl = Path(control_nl).resolve()
                validate_file(
                    control_nl,
                    ".ini",
                    f"namelist control file {control_nl.name}.ini",
                    new_file=False,
                )
                namelist_collection_dict[control_nl.name] = read_config(control_nl)
            else:
                logging.warning(
                    f"Control namelist is None for {control_nl.name}, using model default"
                )
        # - create_case
        cesmroot = Path(simulation_setup["create_case"]["cesmroot"]).resolve()
        validate_directory(cesmroot, "CESM root directory")
        add_CIME_paths_and_import(cesmroot)

        return CheckedCreatePPEConfig(
            **self.__dict__,
            simulation_setup=simulation_setup,
            baseroot=baseroot,
            basecasename=basecasename,
            assumed_esm_component=assumed_esm_component,
            paramfile_path=paramfile_path,
            pdim=pdim,
            paramdict=paramdict,
            componentdict=componentdict,
            num_sims=num_sims,
            num_vars=num_vars,
            ensemble_num=ensemble_num,
            namelist_collection_dict=namelist_collection_dict,
            cesmroot=cesmroot,
        )


@dataclass
class CheckedCreatePPEConfig(CreatePPEConfig):
    # Will have the same fields as CreatePPEConfig, but with additional fields:
    simulation_setup: configparser.ConfigParser = field(
        default=None, metadata={"help": "Parsed simulation setup file"}
    )
    # - ppe_settings
    baseroot: Path = field(
        default=None, metadata={"help": "Path to the base case root directory"}
    )
    basecasename: str = field(default=None, metadata={"help": "Name of the base case"})
    assumed_esm_component: str = field(
        default=None,
        metadata={
            "help": "Assumed ESM component for entries that does not have a specified component attribute in paramfile"
        },
    )
    # - paramfile
    paramfile_path: Path = field(
        default=None, metadata={"help": "Path to the paramfile"}
    )
    pdim: str = field(
        default=None,
        metadata={"help": "Dimension of ensamble member count in paramfile"},
    )
    paramdict: dict = field(
        default=None, metadata={"help": "Dictionary of parameters in the paramfile"}
    )
    componentdict: dict = field(
        default=None, metadata={"help": "Dictionary of ESM components in the paramfile"}
    )
    num_sims: int = field(default=None, metadata={"help": "Number of ensemble members"})
    num_vars: int = field(
        default=None, metadata={"help": "Number of variables in the paramfile"}
    )
    ensemble_num: np.ndarray = field(
        default=None, metadata={"help": "Ensemble number in the paramfile"}
    )
    # - namelist_control
    namelist_collection_dict: dict = field(
        default=None,
        metadata={"help": "Dictionary of namelist parsed namelist_control files"},
    )
    # - create_case
    cesmroot: Path = field(
        default=None, metadata={"help": "Path to the CESM root directory"}
    )

    def __post_init__(self):
        # check the arguments
        check_type(self.simulation_setup, configparser.ConfigParser)
        # - ppe_settings
        validate_directory(self.baseroot, "base case root directory")
        check_type(self.baseroot, Path)
        check_type(self.basecasename, str)
        check_type(self.assumed_esm_component, str)
        # - paramfile
        validate_file(self.paramfile_path, ".nc", "paramfile", new_file=False)
        check_type(self.pdim, str)
        check_type(self.paramdict, dict)
        check_type(self.componentdict, dict)
        check_type(self.num_sims, int)
        check_type(self.num_vars, int)
        check_type(self.ensemble_num, np.ndarray)
        # - namelist_control
        check_type(self.namelist_collection_dict, dict)
        for control_nl, nl_dict in self.namelist_collection_dict.items():
            if control_nl is not None:
                check_type(control_nl, str)
                check_type(nl_dict, configparser.ConfigParser)
        # - create_case
        check_type(self.cesmroot, Path)

    def get_checked_and_derived_config(self):
        logging.info(
            f"{self.__class__.__name__} is a dataclass with all derived fields, no further checks are needed."
        )


@dataclass
class BuildPPEConfig(CreatePPEConfig):
    # Override build_only: set as a dummy field, not used in BuildConfig
    build_only: Optional[None] = field(
        default=None, metadata={"help": "Not used in BuildPPEConfig"}
    )

    def __post_init__(self):
        # Set the build_only field to None
        self.build_only = None
        # run parent checks for the variables that are inherited from CreatePPEConfig
        super().__post_init__()

    def get_checked_and_derived_config(self):
        # Run parent checks and get the checked config from CreatePPEConfig
        checked_create_ppe_config: CheckedCreatePPEConfig = (
            super().get_checked_and_derived_config()
        )

        # delete the build_only field from the checked config
        for field in fields(checked_create_ppe_config):
            if field.name == "build_only":
                delattr(checked_create_ppe_config, field.name)

        return CheckedBuildPPEConfig(
            **checked_create_ppe_config.__dict__, build_only=self.build_only
        )


@dataclass
class CheckedBuildPPEConfig(CheckedCreatePPEConfig):
    # Override build_only: set as a dummy field, not used in BuildConfig
    build_only: Optional[bool] = field(
        default=None, metadata={"help": "Not used in CheckedBuildPPEConfig"}
    )

    def get_checked_and_derived_config(self):
        logging.info(
            f"{self.__class__.__name__} is a dataclass with all derived fields, no further checks are needed."
        )


@dataclass
class SubmitPPEConfig(BaseConfig):
    cases: Union[str, Path, list[str], list[Path]] = field(
        default=None,
        metadata={"help": "List of case directories to submit to the queue"},
    )

    def __post_init__(self):
        # run parent checks for the variables that are inherited from BaseConfig
        super().__post_init__()
        # check the arguments
        if self.cases is None:
            raise ValueError(
                "cases is required. Please provide a valid list of case directories."
            )
        check_type(self.cases, (str, Path, list))
        if isinstance(self.cases, list):
            for case in self.cases:
                check_type(case, (str, Path))

    def get_checked_and_derived_config(self):
        """Check and handle arguments for the PPE configuration."""
        super().get_checked_and_derived_config()

        # cases
        if isinstance(self.cases, str):
            self.cases = [self.cases]
        elif isinstance(self.cases, Path):
            self.cases = [self.cases]
        elif isinstance(self.cases, list) and all(
            isinstance(case, str) or isinstance(case, Path) for case in self.cases
        ):
            self.cases = [Path(case).resolve() for case in self.cases]
        for case in self.cases:
            validate_directory(case, f"case directory {case.name}")

        return CheckedSubmitPPEConfig(**self.__dict__)


@dataclass
class CheckedSubmitPPEConfig(SubmitPPEConfig):
    # Will have the same fields as SubmitPPEConfig

    def __post_init__(self):
        # check the arguments
        check_type(self.cases, list)
        for case in self.cases:
            check_type(case, Path)

    def get_checked_and_derived_config(self):
        logging.info(
            f"{self.__class__.__name__} is a dataclass with all derived fields, no further checks are needed."
        )
