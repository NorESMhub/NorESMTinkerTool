import os
import time
import logging
import configparser
import numpy as np
from pathlib import Path
from netCDF4 import Dataset
from typing import Union, Optional
from dataclasses import dataclass, fields, field

from tinkertool.utils.read_files import read_config
from tinkertool.utils.config_utils import BaseConfig, CheckedBaseConfig
from tinkertool.setup.setup_cime_connection import add_CIME_paths_and_import
from tinkertool.utils.check_arguments import validate_file, validate_directory, check_type

def get_ncattr_or_default(var, attr, default=None):
    try:
        return var.getncattr(attr)
    except AttributeError:
        return default

@dataclass(kw_only=True)
class CreatePPEConfig(BaseConfig):

    # Core required fields
    simulation_setup_path:  Path = field(metadata={"help": "Path to user defined configuration file for simulation setup."})
    # Optional fields with defaults
    build_base_only:        bool = field(default=False, metadata={"help": "Only build the base case - not PPE members"})
    build_only:             bool = field(default=False, metadata={"help": "Only build the PPE and not submit them to the queue"})
    clone_only_during_build:bool = field(default=False, metadata={"help": "Only clone the base case and not build the PPE members. This is useful if you have already built the base_case."})
    keepexe:                bool = field(default=False, metadata={"help": "Reuse the executable for the base case instead of building a new one for each member"})
    overwrite:              bool = field(default=False, metadata={"help": "Overwrite existing cases if they exist"})

    def __post_init__(self):
        # run parent checks for the variables that are inherited from BaseConfig
        super().__post_init__()
        # check the arguments
        if self.simulation_setup_path is None:
            raise ValueError("simulation_setup_path is required. Please provide a valid path to the simulation setup file.")
        validate_file(self.simulation_setup_path, ".ini", "simulation setup file", new_file=False)
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

    def get_checked_and_derived_config(self) -> 'CheckedCreatePPEConfig':
        """Check and handle arguments for the PPE configuration."""
        # Create log file path (from parent class logic)
        time_str = time.strftime("%Y%m%d-%H%M%S")
        log_file = Path(self.log_dir).joinpath(f'tinkertool_{time_str}.log')

        # derived fields - we unpack the simulation setup file
        simulation_setup: configparser.ConfigParser = read_config(self.simulation_setup_path)
        # - ppe_settings
        baseroot = Path(simulation_setup['ppe_settings']['baseroot']).resolve()
        basecasename = simulation_setup['ppe_settings']['basecasename']
        ## - paramfile
        pdim: str = simulation_setup['ppe_settings']['pdim']
        paramfile_path: Path = Path(simulation_setup['ppe_settings']['paramfile']).resolve()
        validate_file(paramfile_path, ".nc", "paramfile", new_file=False)
        paramfile: Dataset = Dataset(paramfile_path, 'r')
        if pdim not in list(paramfile.dimensions.keys()):
            raise SystemExit(f"ERROR: {pdim} is not a valid dimension in {paramfile_path}. \nParamfile dimensions are: {list(paramfile.dimensions.keys())}")
        paramdict: dict = {k: v[:] for k, v in paramfile.variables.items() if k != pdim}
        componentdict: dict = {}
        for param, paramvalue in paramdict.items():
            esm_component = get_ncattr_or_default(paramvalue, 'esm_component', None)
            if esm_component is None:
                err_msg = f"Parameter {param} in paramfile {paramfile_path} does not have an 'esm_component' attribute."
                logging.error(err_msg)
                raise SystemExit(err_msg)
            componentdict[param] = esm_component
        num_sims = paramfile.dimensions[pdim].size
        num_vars = len(paramfile.variables.keys())-1
        ensemble_num = paramfile[pdim][:]
        paramfile.close()
        # - namelist_control
        namelist_collection_dict = {}
        for control_nl in simulation_setup['namelist_control'].values():
            if control_nl is not None:
                control_nl = Path(control_nl).resolve()
                validate_file(control_nl, ".ini", f"namelist control file {control_nl.name}.ini", new_file=False)
                namelist_collection_dict[control_nl.name] = read_config(control_nl)
            else:
                logging.warning(f"Control namelist is None for {control_nl.name}, using model default")
        # - create_case
        cesmroot = Path(simulation_setup['create_case']['cesmroot']).resolve()
        validate_directory(cesmroot, "CESM root directory")
        if os.environ.get('CESMROOT') != str(cesmroot):
            logging.warning(f"CESMROOT environment variable is set to {os.environ.get('CESMROOT')}, but the simulation setup file specifies {cesmroot}.")
            logging.warning("This may cause issues with CIME paths. Consider choosing one cesmroot.")

        add_CIME_paths_and_import(cesmroot)

        return CheckedCreatePPEConfig(
            **self.__dict__,
            log_file=log_file,
            simulation_setup=simulation_setup,
            baseroot=baseroot,
            basecasename=basecasename,
            paramfile_path=paramfile_path,
            pdim=pdim,
            paramdict=paramdict,
            componentdict=componentdict,
            num_sims=num_sims,
            num_vars=num_vars,
            ensemble_num=ensemble_num,
            namelist_collection_dict=namelist_collection_dict,
            cesmroot=cesmroot
        )

@dataclass(kw_only=True)
class CheckedCreatePPEConfig(CheckedBaseConfig):
    # Include all fields from CreatePPEConfig
    simulation_setup_path:  Path = field(metadata={"help": "Path to user defined configuration file for simulation setup."})
    build_base_only:        bool = field(default=False, metadata={"help": "Only build the base case - not PPE members"})
    build_only:             bool = field(default=False, metadata={"help": "Only build the PPE and not submit them to the queue"})
    clone_only_during_build:bool = field(default=False, metadata={"help": "Only clone the base case and not build the PPE members"})
    keepexe:                bool = field(default=False, metadata={"help": "Reuse the executable for the base case"})
    overwrite:              bool = field(default=False, metadata={"help": "Overwrite existing cases if they exist"})
    # Additional derived/checked fields:
    simulation_setup:       configparser.ConfigParser = field(metadata={"help": "Parsed simulation setup file"})
    # - ppe_settings
    baseroot:               Path = field(metadata={"help": "Path to the base case root directory"})
    basecasename:           str = field(metadata={"help": "Name of the base case"})
    # - paramfile
    paramfile_path:         Path = field(metadata={"help": "Path to the paramfile"})
    pdim:                   str = field(metadata={"help": "Dimension of ensemble member count in paramfile"})
    paramdict:              dict = field(metadata={"help": "Dictionary of parameters in the paramfile"})
    componentdict:          dict = field(metadata={"help": "Dictionary of ESM components in the paramfile"})
    num_sims:               int = field(metadata={"help": "Number of ensemble members"})
    num_vars:               int = field(metadata={"help": "Number of variables in the paramfile"})
    ensemble_num:           np.ndarray = field(metadata={"help": "Ensemble number in the paramfile"})
    # - namelist_control
    namelist_collection_dict: dict = field(metadata={"help": "Dictionary of namelist parsed namelist_control files"})
    # - create_case
    cesmroot:              Path = field(metadata={"help": "Path to the CESM root directory"})

    def __post_init__(self):
        # check the arguments
        check_type(self.simulation_setup, configparser.ConfigParser)
        # - ppe_settings
        validate_directory(self.baseroot, "base case root directory")
        check_type(self.baseroot, Path)
        check_type(self.basecasename, str)
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

    def get_checked_and_derived_config(self) -> 'CheckedCreatePPEConfig':
        logging.info(f"{self.__class__.__name__} is a dataclass with all derived fields, no further checks are needed.")
        return self

@dataclass(kw_only=True)
class BuildPPEConfig(CreatePPEConfig):
    # Override build_only: set as a dummy field, not used in BuildConfig
    build_only: Optional[None] = field(
        default=None,
        metadata={"help": "Not used in BuildPPEConfig"}
    )

    def __post_init__(self):
        # Set the build_only field to None
        self.build_only = None  # Not used in BuildPPEConfig
        # run parent checks for the variables that are inherited from CreatePPEConfig
        super().__post_init__()


    def get_checked_and_derived_config(self) -> 'CheckedBuildPPEConfig':
        # Run parent checks and get the checked config from CreatePPEConfig
        checked_create_ppe_config: CheckedCreatePPEConfig = super().get_checked_and_derived_config()

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

    def get_checked_and_derived_config(self) -> 'CheckedBuildPPEConfig':
        self.build_only = None  # Not used in CheckedBuildPPEConfig
        logging.info(f"{self.__class__.__name__} is a dataclass with all derived fields, no further checks are needed.")
        return self

@dataclass(kw_only=True)
class SubmitPPEConfig(BaseConfig):

    cases:  Union[str, Path, list[str], list[Path]] = field(metadata={"help": "List of case directories to submit to the queue"})

    def __post_init__(self):
        # run parent checks for the variables that are inherited from BaseConfig
        super().__post_init__()
        # check the arguments
        if self.cases is None:
            raise ValueError("cases is required. Please provide a valid list of case directories.")
        # cases
        if isinstance(self.cases, str):
            self.cases = [Path(self.cases).resolve()]
        elif isinstance(self.cases, Path):
            self.cases = [self.cases.resolve()]
        elif isinstance(self.cases, list) and all(isinstance(case, str) or isinstance(case, Path) for case in self.cases):
            self.cases = [Path(case).resolve() for case in self.cases]
        else:
            raise TypeError("cases must be a string, Path, or a list of strings or Paths.")
        for case in self.cases:
            validate_directory(case, f"case directory {case.name}")

    def get_checked_and_derived_config(self) -> 'CheckedSubmitPPEConfig':
        """Check and handle arguments for the PPE configuration."""
        # Create log file path (from parent class logic)
        time_str = time.strftime("%Y%m%d-%H%M%S")
        log_file = Path(self.log_dir).joinpath(f'tinkertool_{time_str}.log')

        return CheckedSubmitPPEConfig(**self.__dict__, log_file=log_file)

@dataclass(kw_only=True)
class CheckedSubmitPPEConfig(CheckedBaseConfig):
    # Include fields from SubmitPPEConfig
    cases: Union[str, Path, list[str], list[Path]] = field(metadata={"help": "List of case directories to submit to the queue"})

    def get_checked_and_derived_config(self) -> 'CheckedSubmitPPEConfig':
        logging.info(f"{self.__class__.__name__} is a dataclass with all derived fields, no further checks are needed.")
        return self