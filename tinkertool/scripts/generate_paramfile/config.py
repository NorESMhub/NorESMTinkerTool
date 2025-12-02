import sys
import logging
import configparser
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field

from tinkertool import NorESMTinkerTool_abspath
from tinkertool.utils.config_utils import BaseConfig, CheckedBaseConfig
from tinkertool.utils.read_files import read_config
from tinkertool.utils.check_arguments import validate_file, check_type
from tinkertool.utils.make_chem_in import check_if_chem_mech_is_perterbed
from tinkertool.utils.make_land_parameterfiles import check_if_ctsm_param_is_perturbed, check_if_fates_param_is_perturbed


import io
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
    params:                     list = field(default=None, metadata={"help": "List of parameters to be sampled, have to be defined in param_ranges_inpath. If unspecified all parameters in param_ranges_inpath will be used"})
    exclude_default:            bool = field(default=False, metadata={"help": "Whether to exclude the default parameter value in the output file in nmb_sim=0. Using this flag will skip nmb_sim=0. Default is to include default value."})

    # --- Derived fields (populated by get_checked_and_derived_config) ---
    param_ranges:       configparser.ConfigParser = field(init=False, default=None)
    nparams:            int = field(init=False, default=0)
    scramble:           bool = field(init=False, default=True)
    nmb_sim_dim:        np.ndarray = field(init=False, default=None)
    change_chem_mech:   bool = field(init=False, default=False)
    change_ctsm_params: bool = field(init=False, default=False)
    change_fates_params:bool = field(init=False, default=False)

    def __post_init__(self):
        """Performs initial, lightweight validation of user-provided fields."""
        # param_ranges_inpath
        validate_file(self.param_ranges_inpath, '.ini', "Parameter ranges file as .ini format", new_file=False)
        # param_sample_outpath
        validate_file(self.param_sample_outpath, '.nc', "output parameter file with .nc extension", new_file=True)
        # nmb_sim
        check_type(self.nmb_sim, int)
        if self.nmb_sim <= 0:
            raise ValueError(f"Number of ensemble members must be greater than 0. Given: {self.nmb_sim}.")
        # optimization
        if self.optimization is not None and self.optimization not in ['random-cd', 'lloyd']:
            raise ValueError(f"Invalid optimization method: {self.optimization}. Must be 'random-cd' or 'lloyd'.")
        # params
        if self.params is not None:
            check_type(self.params, list)
            if not all(isinstance(p, str) for p in self.params):
                raise TypeError("All items in 'params' list must be strings.")
        
        super().__post_init__()

    def get_checked_and_derived_config(self) -> 'ParameterFileConfig':
        """
        Performs full, I/O-dependent validation and populates derived fields on the instance.
        This method should be called once at the start of the application.
        It now returns `self`.
        """
        # If derived fields are already populated, we can assume this has been run.
        if self.param_ranges is not None:
            logging.debug("Configuration already checked. Skipping full validation.")
            return self

        # --- Read files and perform heavy validation ---
        self.param_ranges = read_config(self.param_ranges_inpath)

        # --- Populate derived fields ---
        # params
        if self.params is not None and len(self.params) > 0:
            for param in self.params:
                if param not in self.param_ranges:
                    raise ValueError(f"Parameter '{param}' not found in parameter ranges file {self.param_ranges_inpath}.")
            # Subset param_ranges to only include specified params
            for section in list(self.param_ranges.sections()):
                if section not in self.params:
                    self.param_ranges.remove_section(section)
        else:
            self.params = list(self.param_ranges.sections())
        self.nparams = len(self.params)

        # param_sample_outpath (interactive check)
        if self.param_sample_outpath.exists():
            overwrite = input(f"Output file {self.param_sample_outpath} already exists. Overwrite? (y/n): ").strip().lower()
            if overwrite != 'y':
                logging.info(f"Exiting without overwriting existing file.")
                sys.exit(0)
        else:
            self.param_sample_outpath.parent.mkdir(parents=True, exist_ok=True)

        # Check for perturbations and validate corresponding files
        self.change_chem_mech = check_if_chem_mech_is_perterbed(str(self.param_ranges_inpath))
        if self.change_chem_mech:
            if self.chem_mech_file is None:
                raise ValueError("Chemistry perturbations detected, but 'chem_mech_file' was not provided.")
            validate_file(self.chem_mech_file, '.in', "Chemistry mechanism file", new_file=False)

        str_buffer = io.StringIO()
        self.param_ranges.write(str_buffer)
        cfg_str = str_buffer.getvalue()
        self.change_ctsm_params = check_if_ctsm_param_is_perturbed(cfg_str)
        if self.change_ctsm_params:
            if self.ctsm_default_param_file is None:
                raise ValueError("CTSM perturbations detected, but 'ctsm_default_param_file' was not provided.")
            validate_file(self.ctsm_default_param_file, '.nc', "Default CTSM parameter file", new_file=False)

        self.change_fates_params = check_if_fates_param_is_perturbed(str(self.param_ranges_inpath))
        if self.change_fates_params:
            if self.fates_default_param_file is None:
                raise ValueError("FATES perturbations detected, but 'fates_default_param_file' was not provided.")
            validate_file(self.fates_default_param_file, '.nc', "Default FATES parameter file", new_file=False)

        # tinkertool_output_dir
        self.tinkertool_output_dir.mkdir(parents=True, exist_ok=True)

        # avoid_scramble
        self.scramble = not self.avoid_scramble

        # exclude_default
        if self.exclude_default:
            if self.nmb_sim == 0:
                raise ValueError("nmb_sim=0 is not allowed when exclude_default=True.")
            self.nmb_sim_dim = np.arange(1, self.nmb_sim + 1)
        else:
            self.nmb_sim_dim = np.arange(0, self.nmb_sim + 1)

        logging.info("Configuration successfully checked and derived fields populated.")
        return self


