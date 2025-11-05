import time
import logging
import argparse

from pathlib import Path
from typing import TypeVar, Type
from dataclasses import dataclass, fields, field, MISSING

from tinkertool import NorESMTinkerTool_abspath
from tinkertool.utils.custom_logging import setup_logging
from tinkertool.utils.check_arguments import validate_directory

# --- Decorator to add config/CLI helper methods to dataclass ---
TypeVarT = TypeVar("TypeVarT")

def add_config_helpers(cls: Type[TypeVarT]) -> Type[TypeVarT]:
    """Decorator to add CLI/config helper methods to a dataclass."""
    # Use type: ignore to suppress Pylance warnings about dynamic attribute assignment
    cls.help = classmethod(_help)  # type: ignore
    cls.from_cli = classmethod(_from_cli)  # type: ignore
    cls.describe = _describe  # type: ignore
    return cls

def _help(cls: Type[TypeVarT]) -> None:
    if not hasattr(cls, "__dataclass_fields__"):
        raise TypeError(f"{cls.__name__} is not a dataclass.")

    if logging.getLogger().hasHandlers():
        logging.info(f"Dataclass '{cls.__name__}' expects the following fields:")
        for inputfield in fields(cls):  # type: ignore - valid because we hasattr(cls, "__dataclass_fields__")
            desc = inputfield.metadata.get("help", "")
            if inputfield.default is not MISSING:
                desc = f"{desc} (default: {inputfield.default!r})"
            else:
                desc = f"{desc} (required)"
            logging.info(f"  {inputfield.name.ljust(25)}: {str(inputfield.type).ljust(25)} {desc}")
    else:
        print(f"Dataclass '{cls.__name__}' expects the following fields:")
        for inputfield in fields(cls):  # type: ignore - valid because we hasattr(cls, "__dataclass_fields__")
            desc = inputfield.metadata.get("help", "")
            if inputfield.default is not MISSING:
                desc = f"{desc} (default: {inputfield.default!r})"
            else:
                desc = f"{desc} (required)"
            print(f"  {inputfield.name.ljust(25)}: {str(inputfield.type).ljust(25)} {desc}")

def _from_cli(cls: Type[TypeVarT]) -> TypeVarT:
    """Parse CLI args and return a dataclass instance."""
    parser = argparse.ArgumentParser(description=cls.__doc__)
    for fld in fields(cls):  # type: ignore
        arg_name = f"--{fld.name.replace('_', '-')}"
        help_text = fld.metadata.get("help", "")
        required = fld.default is MISSING
        default = None if required else fld.default

        # Handle bools with argparse actions
        if fld.type == bool:
            parser.add_argument(
                arg_name,
                help=help_text + (" (default: False)" if not required else ""),
                action="store_true" if default is not True else "store_false"
            )
            continue

        if fld.type == Path:
            parser.add_argument(
                arg_name,
                type=Path,
                help=help_text + (" (default: None)" if not required else ""),
                required=required,
                default=default
            )
            continue

        # Handle other types
        try:
            parser.add_argument(
                arg_name,
                type=fld.type,
                help=help_text,
                required=required,
                default=default
            )
        except ValueError:
            # If type is not directly callable (e.g., Optional[str]), use str as fallback
            parser.add_argument(
                arg_name,
                type=str,
                help=help_text,
                required=required,
                default=default
            )

    args = parser.parse_args()
    return cls(**vars(args))

def _describe(
    self,
    return_string: bool = False
) -> str | None:
    """Prints or returns string describing the dataclass object.

    Parameters
    ----------
    return_string : bool, optional
        If True, return the description as a string instead of
        printing it, by default False

    Returns
    -------
    str | None
        The description of the dataclass instance, or None if
        not returning as string
    """
    lines = [f"Instance of dataclass '{self.__class__.__name__}':"]
    for fld in fields(self):
        value = getattr(self, fld.name)
        desc = fld.metadata.get("help", "")
        lines.append(f"  {fld.name.ljust(20)} = {value!r} ({fld.type}) | {desc}")
    if return_string:
        return "\n".join(lines)

    if logging.getLogger().hasHandlers():
        logging.info("\n".join(lines))
    else:
        print("\n".join(lines))

@dataclass
@add_config_helpers # add help, from_cli, describe methods
class BaseConfig:
    """Base dataclass for parameter file generation configuration."""
    verbose:    int = field(default=0, metadata={"help": "Increase verbosity level (0: WARNING, 1: INFO, 2: INFO_DETAILED, 3: DEBUG)"})
    log_dir:    Path | str = field(default="", metadata={"help": "Path to the log directory where logs will be written. If not specified, logs will be printed in current work directory."})
    log_mode:   str = field(default="w", metadata={"help": "Mode for opening the log file ('w' for write, 'a' for append)"})

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
        # log_mode
        if self.log_mode not in ["w", "a"]:
            raise ValueError(f"Invalid log mode: {self.log_mode}. Must be 'w' or 'a'.")

    def get_checked_and_derived_config(self):
        time_str = time.strftime("%Y%m%d-%H%M%S")
        log_file = Path(self.log_dir).joinpath(f'tinkertool_{time_str}.log')
        return CheckedBaseConfig(
            **self.__dict__,
            log_file=log_file
        )

@dataclass(kw_only=True)
class CheckedBaseConfig(BaseConfig):
    """BaseConfig subclass that performs argument checking in __post_init__."""

    log_file: Path = field(default_factory=lambda: NorESMTinkerTool_abspath.parent.joinpath('output', f"tinkertool.{time.strftime('%Y%m%d-%H%M%S')}.log"), metadata={"help": "Log file path (set automatically)"})

    def __post_init__(self):
        # set up logging
        if not logging.getLogger('tinkertool_log').handlers:
            setup_logging(self.verbose, self.log_file, self.log_mode, 'tinkertool_log')
        super().__post_init__()
        # Additional argument checks can be added here in subclasses
