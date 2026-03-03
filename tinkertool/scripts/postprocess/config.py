import time
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from tinkertool.utils.config_utils import BaseConfig, CheckedBaseConfig
from tinkertool.utils.check_arguments import validate_directory, check_type


VALID_OUTPUT_FORMATS = ('zarr', 'netcdf4', 'both')


@dataclass(kw_only=True)
class ReshapeRechunkConfig(BaseConfig):
    """Reshape and rechunk PPE output into one-file-per-variable Zarr/NetCDF4 stores.

    Scans *input_dir* for per-member subdirectories, opens all matching NetCDF
    files for each member, concatenates them along a new ``ens_member``
    dimension, rechunks the result (time for 2-D variables; time + vertical
    level for 3-D variables), and writes one output file per variable.
    """

    input_dir: Path = field(
        metadata={"help": "Root directory whose subdirectories each contain one ensemble member's NetCDF output files."}
    )
    output_dir: Path = field(
        metadata={"help": "Directory where reshaped/rechunked output files are written (created if absent)."}
    )
    output_format: str = field(
        default="both",
        metadata={"help": f"Output format: one of {VALID_OUTPUT_FORMATS}. (default: 'both')"}
    )
    time_chunk: int = field(
        default=12,
        metadata={"help": "Chunk size along the time dimension. (default: 12)"}
    )
    lev_chunk: int = field(
        default=-1,
        metadata={"help": "Chunk size along the vertical dimension; -1 means use the full level dimension. (default: -1)"}
    )
    file_pattern: str = field(
        default="*.nc",
        metadata={"help": "Glob pattern used to find NetCDF files inside each member subdirectory. (default: '*.nc')"}
    )
    variables: Optional[str] = field(
        default=None,
        metadata={"help": "Comma-separated list of variable names to process. If omitted all variables are processed."}
    )

    def __post_init__(self):
        super().__post_init__()
        if self.input_dir is None:
            raise ValueError("input_dir is required.")
        self.input_dir = Path(self.input_dir).resolve()
        validate_directory(self.input_dir, "input directory")
        if self.output_dir is None:
            raise ValueError("output_dir is required.")
        self.output_dir = Path(self.output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.output_format not in VALID_OUTPUT_FORMATS:
            raise ValueError(
                f"Invalid output_format '{self.output_format}'. "
                f"Must be one of {VALID_OUTPUT_FORMATS}."
            )
        check_type(self.time_chunk, int)
        if self.time_chunk <= 0:
            raise ValueError(f"time_chunk must be a positive integer, got {self.time_chunk}.")
        check_type(self.lev_chunk, int)
        if self.lev_chunk != -1 and self.lev_chunk <= 0:
            raise ValueError(
                f"lev_chunk must be a positive integer or -1 (full dimension), got {self.lev_chunk}."
            )
        check_type(self.file_pattern, str)

    def get_checked_and_derived_config(self) -> 'CheckedReshapeRechunkConfig':
        time_str = time.strftime("%Y%m%d-%H%M%S")
        log_file = Path(self.log_dir).joinpath(f'tinkertool_{time_str}.log')

        variables_list: Optional[list[str]] = None
        if self.variables is not None:
            variables_list = [v.strip() for v in self.variables.split(',') if v.strip()]

        if self.__dict__.get('log_file', log_file) is not None:
            log_file = self.__dict__.get('log_file', log_file)
        if 'log_file' in self.__dict__:
            del self.__dict__['log_file']

        return CheckedReshapeRechunkConfig(
            **self.__dict__,
            log_file=log_file,
            variables_list=variables_list,
        )


@dataclass(kw_only=True)
class CheckedReshapeRechunkConfig(CheckedBaseConfig):
    """Validated configuration for reshape-and-rechunk with all derived fields populated."""

    input_dir: Path = field(
        metadata={"help": "Validated root directory for per-member NetCDF output."}
    )
    output_dir: Path = field(
        metadata={"help": "Validated output directory."}
    )
    output_format: str = field(
        default="both",
        metadata={"help": "Output format."}
    )
    time_chunk: int = field(
        default=12,
        metadata={"help": "Chunk size along time."}
    )
    lev_chunk: int = field(
        default=-1,
        metadata={"help": "Chunk size along the vertical dimension (-1 = full)."}
    )
    file_pattern: str = field(
        default="*.nc",
        metadata={"help": "Glob pattern for NetCDF files."}
    )
    variables: Optional[str] = field(
        default=None,
        metadata={"help": "Raw comma-separated variable list string (may be None)."}
    )
    # Derived field
    variables_list: Optional[list[str]] = field(
        default=None,
        metadata={"help": "Parsed list of variable names to process (None = all)."}
    )

    def __post_init__(self):
        super().__post_init__()
        validate_directory(self.input_dir, "input directory")
        check_type(self.output_format, str)
        if self.output_format not in VALID_OUTPUT_FORMATS:
            raise ValueError(
                f"Invalid output_format '{self.output_format}'. "
                f"Must be one of {VALID_OUTPUT_FORMATS}."
            )
        check_type(self.time_chunk, int)
        check_type(self.lev_chunk, int)
        check_type(self.file_pattern, str)

    def get_checked_and_derived_config(self) -> 'CheckedReshapeRechunkConfig':
        logging.info(
            f"{self.__class__.__name__} is already fully checked; no further processing needed."
        )
        return self
