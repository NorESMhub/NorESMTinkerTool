import logging
from pathlib import Path
from typing import Optional, Union

from tinkertool.utils.check_arguments import validate_file

INFO_DETAILED = 15

def patch_info_detailed():
    """Patch Logger class to add info_detailed method and custom level."""
    if not hasattr(logging.Logger, 'info_detailed'):
        logging.addLevelName(INFO_DETAILED, 'INFO_DETAILED')
        def info_detailed(self, message, *args, **kwargs):
            if self.isEnabledFor(INFO_DETAILED):
                self._log(INFO_DETAILED, message, args, **kwargs)
        setattr(logging.Logger, 'info_detailed', info_detailed)

def log_info_detailed(logger_name: str, message: str):
    """Helper function to log info_detailed messages with proper type handling."""
    logger = logging.getLogger(logger_name)
    if hasattr(logger, 'info_detailed'):
        logger.info_detailed(message)  # type: ignore[attr-defined]
    else:
        logger.info(f"[DETAILED] {message}")

def setup_logging(
    verbosity: int,
    log_file: Optional[Union[str, Path]] = None,
    log_mode: str = 'w',
    logger_name: str = 'tinkertool_log'
):
    """Set up logging configuration. Both for the root logger and a custom logger.

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
    logger_name : str
        Name of the logger. Default is 'tinkertool_log'.
    """
    # root logger do not have a info_detailed level
    # so 2 would yeald debug level in root logger
    # therefore we set the root logger to one level lower than the custom logger
    # when verbosity is greater than 1.
    root_verbosity = verbosity if verbosity <= 1 else verbosity - 1
    root_logger(root_verbosity, log_file, log_mode)
    return custom_logging(verbosity, log_file, log_mode, logger_name)

def root_logger(
    verbosity: int,
    log_file: Optional[Union[str, Path]] = None,
    log_mode: str = 'w',
):
    """
    Set up the root logger with a stream handler and an optional file handler.

    If a log file is provided, the root logger writes to a file with the same name as `log_file`,
    but with `.root` inserted before the suffix (e.g., `build_ppe.log` → `build_ppe.root.log`).

    Parameters
    ----------
    verbosity : int
        Verbosity level for logging. 0 for WARNING, 1 for INFO, 3 for DEBUG.
    log_file : str or Path, optional
        Path to the base log file. If provided, the root logger writes to a file with
        `.root` added to the stem (e.g., `mylog.log` → `mylog.root.log`). If None, logs
        are not written to a file.
    log_mode : str, default 'w'
        Mode to open the log file. 'w' for overwrite, 'a' for append.

    Returns
    -------
    None

    Examples
    --------
    >>> root_logger(1, Path("output.log"), "w")
    # Logs to both stdout and 'output.root.log' at INFO level.

    >>> root_logger(0)
    # Logs only to stdout at WARNING level.
    """
    level = {0: logging.WARNING, 1: logging.INFO, 3: logging.DEBUG}.get(verbosity, logging.DEBUG)

    handlers = [logging.StreamHandler()]
    if log_file is not None:
        root_log_file = Path(log_file).with_name(Path(log_file).stem + ".root" + Path(log_file).suffix)
        validate_file(root_log_file, '.log', "log file", new_file=True)
        if not root_log_file.exists():
            root_log_file.parent.mkdir(parents=True, exist_ok=True)
            root_log_file.touch()
        handlers.append(logging.FileHandler(str(root_log_file), mode=log_mode))

    # Remove any existing handlers to avoid duplicate logs
    root_logger_obj = logging.getLogger()
    for h in root_logger_obj.handlers[:]:
        root_logger_obj.removeHandler(h)

    for handler in handlers:
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s/ROOT] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        root_logger_obj.addHandler(handler)

    root_logger_obj.setLevel(level)

def custom_logging(
    verbosity: int,
    log_file: Optional[Union[str, Path]] = None,
    log_mode: str = 'w',
    logger_name: str = 'tinkertool_log'
):
    """Set up logging configuration. for a custom logger with a custom level.

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
    logger_name : str
        Name of the logger. Default is 'tinkertool_log'.
    """
    # Patch the logging module to add info_detailed level
    patch_info_detailed()

    # Map verbosity to logging levels
    level = {0: logging.WARNING, 1: logging.INFO, 2: INFO_DETAILED, 3: logging.DEBUG}.get(verbosity, logging.DEBUG)

    # Set up the logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False
    # Remove all existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create new handlers
    handlers = [logging.StreamHandler()]
    if log_file is not None:
        log_file = Path(log_file).resolve()
        validate_file(log_file, '.log', "log file", new_file=True)
        if not log_file.exists():
            log_file.parent.mkdir(parents=True, exist_ok=True)
            log_file.touch()
        handlers.append(logging.FileHandler(str(log_file), mode=log_mode))
    # Set the formatter for the handlers
    formatter = logging.Formatter("%(asctime)s [%(levelname)s/{}] %(message)s".format(logger_name.capitalize()), datefmt="%Y-%m-%d %H:%M:%S")

    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger