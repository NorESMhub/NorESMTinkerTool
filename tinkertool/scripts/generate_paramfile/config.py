import sys
import time
import logging
import configparser
import numpy as np
from pathlib import Path
from dataclasses import dataclass, fields, field, MISSING

from tinkertool import VALID_COMPONENTS, NorESMTinkerTool_abspath
from tinkertool.utils.config_utils import BaseConfig, CheckedBaseConfig
from tinkertool.utils.read_files import read_config
from tinkertool.utils.check_arguments import validate_file, check_type
from tinkertool.utils.make_chem_in import check_if_chem_mech_is_perterbed
from tinkertool.utils.make_land_parameterfiles import check_if_ctsm_param_is_perturbed, check_if_fates_param_is_perturbed

# ------------------------ #
# --- Global variables --- #
# ------------------------ #
default_output_dir = NorESMTinkerTool_abspath.joinpath('output')    # NorESMTinkerTool/output

@dataclass(kw_only=True)
class ParameterFileConfig(BaseConfig):
    """Parameter file generation configuration."""

    # Core required fields (validated in __post_init__)
    param_ranges_inpath:        Path = field(metadata={"help": "Path to the parameter ranges file in .ini format"})
    param_sample_outpath:       Path = field(metadata={"help": "Path to the output parameter file with .nc extension"})
    nmb_sim:                    int = field(metadata={"help": "Number of ensemble members."})
    # Optional parameter file specific fields
    chem_mech_file:             Path | None = field(default=None, metadata={"help": "Path to the chemistry mechanism file, default None will will not modify chemistry mechanism."})
    ctsm_default_param_file:    Path | None = field(default=None, metadata={"help": "Path to the default CTSM parameter file in netCDF format, default None will not modify CTSM parameters"})
    fates_default_param_file:   Path | None = field(default=None, metadata={"help": "Path to the default FATES parameter file in netCDF format, default None will not modify FATES parameters"})
    tinkertool_output_dir:      Path = field(default=Path(default_output_dir).resolve(), metadata={"help": "Path to the output directory for files produced by TinkerTool, default will use NorESMTinkerTool/output"})
    optimization:               str | None = field(default=None, metadata={"help": "Whether to enable optimization after sampling, valid random-cd or lloyd. Default None."})
    avoid_scramble:             bool = field(default=False, metadata={"help": "Overwrite the default scramble of hypercube, i.e. scramble=False to center samples within cells of a multi-dimensional grid. If it is not called, samples are randomly placed within cells of the grid."})
    params:                     list = field(default_factory=list, metadata={"help": "List of parameters to be sampled, have to be defined in param_ranges_inpath. If unspecified all parameters in param_ranges_inpath will be used"})
    exclude_default:            bool = field(default=False, metadata={"help": "Whether to exclude the default parameter value in the output file in nmb_sim=0. Using this flag will skip nmb_sim=0. Default is to include default value."})

    def __post_init__(self):
        # check the arguments
        # param_ranges_inpath
        if self.param_ranges_inpath is None:
            raise ValueError("param_ranges_inpath is required!")
        validate_file(self.param_ranges_inpath, '.ini', "Parameter ranges file as .ini format", new_file=False)
        # param_sample_outpath
        if self.param_sample_outpath is None:
            raise ValueError("param_sample_outpath is required!")
        # Validate main output file (.nc extension)
        validate_file(self.param_sample_outpath, '.nc', "output parameter file with .nc extension", new_file=True)
        # nmb_sim
        check_type(self.nmb_sim, int)
        if self.nmb_sim <= 0:
            raise ValueError(f"Number of ensemble members must be greater than 0. Given: {self.nmb_sim}.")
        # optimization
        if self.optimization is not None:
            check_type(self.optimization, str)
            if self.optimization not in ['random-cd', 'lloyd']:
                raise ValueError(f"Invalid optimization method: {self.optimization}. Must be 'random-cd' or 'lloyd'.")
        # avoid_scramble
        check_type(self.avoid_scramble, bool)
        # params
        check_type(self.params, list)
        for param in self.params:
            check_type(param, str)
        # exclude_default
        check_type(self.exclude_default, bool)

        # run the parent __post_init__ method
        super().__post_init__()

    def get_checked_and_derived_config(self) -> 'CheckedParameterFileConfig':
        """Check and handle arguments for the parameter file generation configuration."""
        # Create log file path (from parent class logic)
        import time
        time_str = time.strftime("%Y%m%d-%H%M%S")
        log_file = Path(self.log_dir).joinpath(f'tinkertool_{time_str}.log')

        # param_ranges_inpath
        if self.param_ranges_inpath is None:
            raise ValueError("param_ranges_inpath is required!")
        assert self.param_ranges_inpath is not None  # Help type checker
        param_ranges: configparser.ConfigParser = read_config(self.param_ranges_inpath)
        # params
        if self.params:  # Check if list is not empty
            self.params = [param.strip() for param in self.params]
            for param in self.params:
                if param not in param_ranges:
                    raise ValueError(f"Parameter '{param}' not found in parameter ranges file {self.param_ranges_inpath}.")
        else:
            self.params = list(param_ranges.sections())
        nparams = len(self.params)
        # param_sample_outpath
        assert self.param_sample_outpath is not None  # Help type checker
        if self.param_sample_outpath.exists():
            overwrite = input(f"Output file {self.param_sample_outpath} already exists. Overwrite? (y/n): ").strip().lower()
            if overwrite != 'y':
                logging.info(f"Output file {self.param_sample_outpath} already exists. Exiting without overwriting.")
                sys.exit(0)
        else:
            self.param_sample_outpath.parent.mkdir(parents=True, exist_ok=True)
        # chem_mech_file
        change_chem_mech = False
        if check_if_chem_mech_is_perterbed(str(self.param_ranges_inpath)):
            change_chem_mech = True
            if self.chem_mech_file is None:
                err_msg = ("Parameter ranges file indicates chemistry mechanism perturbations, "
                           "but no chem_mech_file is provided. Please provide a chemistry mechanism file.")
                logging.error(err_msg)
                raise ValueError(err_msg)
            else:
                validate_file(self.chem_mech_file, '.in', "Chemistry mechanism file", new_file=False)
        # check if CTSM or FATES parameters are perturbed
        # ctsm_default_param_file
        change_ctsm_params = False
        if check_if_ctsm_param_is_perturbed(str(self.param_ranges_inpath)):
            change_ctsm_params = True
            if self.ctsm_default_param_file is None:
                err_msg = ("Parameter ranges file indicates CTSM parameter perturbations, "
                           "but no ctsm_default_param_file is provided. Please provide a default CTSM parameter file.")
                logging.error(err_msg)
                raise ValueError(err_msg)
            else:
                validate_file(self.ctsm_default_param_file, '.nc', "Default CTSM parameter file", new_file=False)
        # fates_default_param_file
        change_fates_params = False
        if check_if_fates_param_is_perturbed(str(self.param_ranges_inpath)):
            change_fates_params = True
            if self.fates_default_param_file is None:
                err_msg = ("Parameter ranges file indicates FATES parameter perturbations, "
                           "but no fates_default_param_file is provided. Please provide a default FATES parameter file.")
                logging.error(err_msg)
                raise ValueError(err_msg)
            else:
                validate_file(self.fates_default_param_file, '.nc', "Default FATES parameter file", new_file=False)
        # tinkertool_output_dir
        self.tinkertool_output_dir = self.tinkertool_output_dir if self.tinkertool_output_dir is not None else default_output_dir
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
                raise ValueError("nmb_sim=0 is not allowed when exclude_default=True. Please set nmb_sim>0 or exclude the flag.")
            nmb_sim_dim = np.arange(1, self.nmb_sim+1)
        else:
            nmb_sim_dim = np.arange(0, self.nmb_sim+1)

        return CheckedParameterFileConfig(
            **self.__dict__,
            log_file=log_file,
            param_ranges=param_ranges,
            nparams=nparams,
            scramble=scramble,
            nmb_sim_dim=nmb_sim_dim,
            change_chem_mech=change_chem_mech,
            change_ctsm_params=change_ctsm_params,
            change_fates_params=change_fates_params
        )

@dataclass(kw_only=True)
class CheckedParameterFileConfig(CheckedBaseConfig):
    """Checked dataclass for parameter file generation configuration."""
    # Include all fields from ParameterFileConfig
    param_ranges_inpath:        Path = field(metadata={"help": "Path to the parameter ranges file in .ini format"})
    param_sample_outpath:       Path = field(metadata={"help": "Path to the output parameter file with .nc extension"})
    nmb_sim:                    int = field(metadata={"help": "Number of ensemble members."})
    # Optional parameter file specific fields from ParameterFileConfig
    chem_mech_file:             Path | None = field(default=None, metadata={"help": "Path to the chemistry mechanism file"})
    ctsm_default_param_file:    Path | None = field(default=None, metadata={"help": "Path to the default CTSM parameter file in netCDF format"})
    fates_default_param_file:   Path | None = field(default=None, metadata={"help": "Path to the default FATES parameter file in netCDF format"})
    tinkertool_output_dir:      Path = field(default=Path(default_output_dir).resolve(), metadata={"help": "Path to the output directory for files produced by TinkerTool"})
    optimization:               str | None = field(default=None, metadata={"help": "Whether to enable optimazation after sampling"})
    avoid_scramble:             bool = field(default=False, metadata={"help": "Overwrite the default scramble of hypercube"})
    params:                     list = field(default_factory=list, metadata={"help": "List of parameters to be sampled"})
    exclude_default:            bool = field(default=False, metadata={"help": "Whether to exclude the default parameter value in the output file"})

    # Derived/checked configuration fields
    param_ranges:       configparser.ConfigParser = field(default_factory=lambda: configparser.ConfigParser(), metadata={"help": "Parsed parameter ranges file"})
    nparams:            int = field(default=0, metadata={"help": "Number of parameters to be sampled"})
    scramble:           bool = field(default=True, metadata={"help": "Whether to scramble the samples"})
    nmb_sim_dim:        np.ndarray = field(default_factory=lambda: np.array([]), metadata={"help": "Array of ensemble member indices"})
    change_chem_mech:   bool = field(default=False, metadata={"help": "Whether to change the chemistry mechanism file"})
    change_ctsm_params: bool = field(default=False, metadata={"help": "Whether to change CTSM parameters"})
    change_fates_params:bool = field(default=False, metadata={"help": "Whether to change FATES parameters"})

    def __post_init__(self):
        # run the parent __post_init__ method
        super().__post_init__()
        # check the arguments
        # param_ranges
        check_type(self.param_ranges, configparser.ConfigParser)
        if not self.param_ranges.sections():
            raise ValueError(f"Parameter ranges file {self.param_ranges_inpath} is empty or invalid.")
        # nparams
        check_type(self.nparams, int)
        # scramble
        check_type(self.scramble, bool)
        # nmb_sim_dim
        check_type(self.nmb_sim_dim, np.ndarray)
        # change_chem_mech
        check_type(self.change_chem_mech, bool)

    def get_checked_and_derived_config(self) -> 'CheckedParameterFileConfig':
        logging.info(f"{self.__class__.__name__} is a dataclass with all derived fields, no further checks are needed.")
        return self
