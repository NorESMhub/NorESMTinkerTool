import logging
from pathlib import Path
from typing import Optional, Union

from tinkertool.utils.check_arguments import validate_file

def setup_logging(
    verbosity: int,
    log_file: Optional[Union[str, Path]] = None,
    log_mode: str = 'w'
):
    """Set up logging configuration.

    Parameters
    ----------
    verbosity : int
        Verbosity level for logging. 0 for WARNING, 1 for INFO, 2 for INFO_DETAILED, 3 for DEBUG.
    log_file : str or Path, optional
        Path to the log file where logs will be written. If None, logs will not be saved to a file.
        Default is None.
    log_mode : str
        Mode for opening the log file. 'w' for write (overwrite), 'a' for append.
        Default is 'w'.
    """
    INFO_DETAILED = 15
    logging.addLevelName(INFO_DETAILED, 'INFO_DETAILED')

    def info_detailed(self, message, *args, **kwargs):
        if self.isEnabledFor(INFO_DETAILED):
            self._log(INFO_DETAILED, message, args, **kwargs)
    logging.Logger.info_detailed = info_detailed

    # Map verbosity to logging levels
    level = {0: logging.WARNING, 1: logging.INFO, 2: INFO_DETAILED, 3: logging.DEBUG}.get(verbosity, logging.DEBUG)

    # Remove all handlers associated with the root logger object.
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handlers = [logging.StreamHandler()]
    if log_file is not None:
        validate_file(log_file, '.log', "log file", new_file=True)
        if not log_file.exists():
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.touch()
        handlers.append(logging.FileHandler(str(log_file), mode=log_mode))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
        datefmt="%Y-%m-%d %H:%M:%S"
    )