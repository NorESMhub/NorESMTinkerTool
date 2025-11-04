import sys
import time
import configparser
import logging
from dataclasses import MISSING, dataclass, field, fields
from pathlib import Path

import numpy as np
import importlib.resources as pkg_resources

from tinkertool.utils.check_arguments import (
    check_type,
    validate_directory,
    validate_file,
)
from tinkertool.utils.logging import setup_logging
from tinkertool.utils.make_chem_in import (
    check_if_chem_mech_is_perterbed,
    generate_chem_in_ppe,
)
from tinkertool.utils.read_files import read_config

# ------------------------ #
# --- Global variables --- #
# ------------------------ #
with pkg_resources.path("tinkertool.default_config", "default_chem_mech.in") as p:
    default_chem_mech = p.resolve()
    if default_chem_mech is None:
        raise FileNotFoundError("Could not locate default_chem_mech.in resource file")
default_output_dir = Path(__file__).parent.parent.parent.joinpath(
    "output"
)
default_output_dir = Path(__file__).parent.parent.parent.joinpath('output')

@dataclass
class BaseConfig:
    """Base dataclass for parameter file generation configuration."""

    verbose: int = field(
        default=0,
        metadata={
            "help": "Increase verbosity level (0: WARNING, 1: INFO, 2: INFO_DETAILED, 3: DEBUG)"
        },
    )
    log_file: Path | str = field(
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
            raise ValueError(f"Invalid verbosity level: {self.verbose}. Must be 0, 1, 2, or 3.")
        # log_dir
        if self.log_dir is not None:
            self.log_dir = Path(self.log_dir).resolve()
            if not self.log_dir.exists():
                self.log_dir.mkdir(parents=True, exist_ok=True)
            validate_directory(self.log_dir, "Log directory")
        else:
            self.log_dir = Path.cwd()
        time_str = time.strftime("%Y%m%d-%H%M%S")
        self.log_file = self.log_dir.joinpath(f'tinkertool_{time_str}.log')
        # log_mode
        if self.log_mode not in ["w", "a"]:
            raise ValueError(f"Invalid log mode: {self.log_mode}. Must be 'w' or 'a'.")

        # set up logging
        if not logging.getLogger("tinkertool_log").handlers:
            setup_logging(self.verbose, self.log_file, self.log_mode, "tinkertool_log")

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
        return self

@dataclass(kw_only=True)
class ParameterFileConfig(BaseConfig):
    """Parameter file generation configuration.

    This class inherits from BaseConfig.
    """

    # Core required fields (validated in __post_init__)
    param_ranges_inpath:    Path = field(metadata={"help": "Path to the parameter ranges file in .ini format"})
    param_sample_outpath:   Path = field(metadata={"help": "Path to the output parameter file with .nc extension"})
    nmb_sim:                int = field(metadata={"help": "Number of ensemble members."})
    # Optional parameter file specific fields
    
    chem_mech_file: Path = field(
        default=None,
        metadata={
            "help": "Path to the chemistry mechanism file, default None will use NorESMTinkerTool/default_config/default_chem_mech.in"
        },
    )
    tinkertool_output_dir: Path = field(
        default=None,
        metadata={
            "help": "Path to the output directory for files produced by TinkerTool, default None will use NorESMTinkerTool/output"
        },
    )
    nmb_sim: int = field(
        default=30, metadata={"help": "Number of ensemble members, default 30"}
    )
    optimization: str = field(
        default=None,
        metadata={
            "help": "Whether to enable optimazation after sampling, valid random-cd or lloyd. Default None."
        },
    )
    avoid_scramble: bool = field(
        default=False,
        metadata={
            "help": "Overwrite the default scramble of hypercube, i.e. scramble=False to center samples within cells of a multi-dimensional grid. If it is not called, samples are randomly placed within cells of the grid."
        },
    )
    params: list = field(
        default=None,
        metadata={
            "help": "List of parameters to be sampled, have to be defined in param_ranges_inpath. If unspecified all parameters in param_ranges_inpath will be used"
        },
    )
    assumed_esm_component: str = field(
        default="cam",
        metadata={
            "help": "Assume component for parameter. This is used if component is not specified for an entry in the parameter ranges file. Default is 'cam'."
        },
    )
    exclude_default: bool = field(
        default=False,
        metadata={
            "help": "Whether to exclude the default parameter value in the output file in nmb_sim=0. Using this flag will skip nmb_sim=0. Default is to include default value."
        },
    )
    def __post_init__(self):
        # check the arguments
        # param_ranges_inpath
        if self.param_ranges_inpath is None:
            raise ValueError("param_ranges_inpath is required!")
        validate_file(
            self.param_ranges_inpath,
            ".ini",
            "Parameter ranges file as .ini format",
            new_file=False,
        )
        # param_sample_outpath
        if self.param_sample_outpath is None:
            raise ValueError("param_sample_outpath is required!")
        validate_file(
            self.param_sample_outpath,
            ".nc",
            "output parameter file with .nc extension",
            new_file=True,
        )
        # nmb_sim
        check_type(self.nmb_sim, int)
        if self.nmb_sim <= 0:
            raise ValueError(
                f"Number of ensemble members must be greater than 0. Given: {self.nmb_sim}."
            )
        # optimization
        if self.optimization is not None:
            check_type(self.optimization, str)
            if self.optimization not in ["random-cd", "lloyd"]:
                raise ValueError(
                    f"Invalid optimization method: {self.optimization}. Must be 'random-cd' or 'lloyd'."
                )
        # avoid_scramble
        check_type(self.avoid_scramble, bool)
        # params
        if self.params is not None:
            check_type(self.params, list)
            for param in self.params:
                check_type(param, str)
        # assume_component
        valid_components = ["cam", "cice", "clm"]
        if self.assumed_esm_component not in valid_components:
            raise ValueError(
                f"Invalid component: {self.assumed_esm_component}. Must be one of {valid_components}."
            )
        # exclude_default
        check_type(self.exclude_default, bool)

        # run the parent __post_init__ method
        super().__post_init__()

    def get_checked_and_derived_config(self):
        """Check and handle arguments for the parameter file generation configuration."""
        super().get_checked_and_derived_config()

        # param_ranges_inpath
        if self.param_ranges_inpath is None:
            raise ValueError("param_ranges_inpath is required!")
        assert self.param_ranges_inpath is not None  # Help type checker
        param_ranges = read_config(self.param_ranges_inpath)
        # params
        if self.params is not None:
            self.params = [param.strip() for param in self.params]
            for param in self.params:
                if param not in param_ranges:
                    raise ValueError(
                        f"Parameter '{param}' not found in parameter ranges file {self.param_ranges_inpath}."
                    )
        else:
            self.params = param_ranges.sections()
        nparams = len(self.params)
        # param_sample_outpath
        assert self.param_sample_outpath is not None  # Help type checker
        if self.param_sample_outpath.exists():
            overwrite = (
                input(
                    f"Output file {self.param_sample_outpath} already exists. Overwrite? (y/n): "
                )
                .strip()
                .lower()
            )
            if overwrite != "y":
                logging.info(
                    f"Output file {self.param_sample_outpath} already exists. Exiting without overwriting."
                )
                sys.exit(0)
        else:
            self.param_sample_outpath.parent.mkdir(parents=True, exist_ok=True)
        # chem_mech_file
        change_chem_mech = False
        if check_if_chem_mech_is_perterbed(str(self.param_ranges_inpath)):
            change_chem_mech = True
            if self.chem_mech_file is None:
                self.chem_mech_file = default_chem_mech
            else:
                validate_file(
                    self.chem_mech_file,
                    ".in",
                    "Chemistry mechanism file",
                    new_file=False,
                )
        # tinkertool_output_dir
        self.tinkertool_output_dir = (
            self.tinkertool_output_dir
            if self.tinkertool_output_dir is not None
            else default_output_dir
        )
        if not self.tinkertool_output_dir.is_dir():
            self.tinkertool_output_dir.mkdir(parents=True, exist_ok=True)
        # avoid_scramble
        if self.avoid_scramble:
            scramble = False
        else:
            scramble = True
        # exclude_default
        if self.exclude_default:
            if self.nmb_sim == 0:
                raise ValueError(
                    "nmb_sim=0 is not allowed when exclude_default=True. Please set nmb_sim>0 or exclude the flag."
                )
            nmb_sim_dim = np.arange(1, self.nmb_sim + 1)
        else:
            nmb_sim_dim = np.arange(0, self.nmb_sim + 1)

        return CheckedParameterFileConfig(
            **self.__dict__,
            param_ranges=param_ranges,
            nparams=nparams,
            scramble=scramble,
            nmb_sim_dim=nmb_sim_dim,
            change_chem_mech=change_chem_mech,
        )

@dataclass(kw_only=True)
class CheckedParameterFileConfig(ParameterFileConfig):
    """Checked dataclass for parameter file generation configuration."""

    # Will have the same fields as the ParameterFileConfig class, but with additional fields for the checked configuration
    param_ranges:       configparser.ConfigParser = field(default_factory=lambda: configparser.ConfigParser(), metadata={"help": "Parsed parameter ranges file"})
    nparams:            int = field(default=0, metadata={"help": "Number of parameters to be sampled"})
    scramble:           bool = field(default=True, metadata={"help": "Whether to scramble the samples"})
    nmb_sim_dim:        np.ndarray = field(default_factory=lambda: np.array([]), metadata={"help": "Array of ensemble member indices"})
    change_chem_mech:   bool = field(default=False, metadata={"help": "Whether to change the chemistry mechanism file"})

    def __post_init__(self):
        # run the parent __post_init__ method
        super().__post_init__()
        # check the arguments
        # param_ranges
        check_type(self.param_ranges, configparser.ConfigParser)
        if not self.param_ranges.sections():
            raise ValueError(
                f"Parameter ranges file {self.param_ranges_inpath} is empty or invalid."
            )
        # nparams
        check_type(self.nparams, int)
        # scramble
        check_type(self.scramble, bool)
        # nmb_sim_dim
        check_type(self.nmb_sim_dim, np.ndarray)
        # change_chem_mech
        check_type(self.change_chem_mech, bool)

    def get_checked_and_derived_config(self):
        logging.info(f"{self.__class__.__name__} is a dataclass with all derived fields, no further checks are needed.")
        return self
