from pathlib import Path
from typing import Union
from tinkertool.utils.type_check_decorator import type_check_decorator

@type_check_decorator
def validate_file(
    file_path:          Path,
    expected_suffix:    str,
    description:        str,
    new_file:           bool
):
    if not file_path.suffix == expected_suffix:
        raise SystemExit(f"ERROR: {file_path} is not a valid {description}")
    else:
        if new_file and file_path.exists():
            Warning(f"WARNING: {file_path} already exists. It will be overwritten.")
        if not new_file and not file_path.exists():
            raise SystemExit(f"ERROR: {file_path} does not exist. Please provide a valid file path.")

@type_check_decorator
def validate_directory(
    directory_path: Path,
    description: str
):
    if not directory_path.is_dir():
        raise SystemExit(f"ERROR: {directory_path} is not a valid {description}")

def check_type(
    obj: object,
    expected_type: Union[type, list[type]],
):
    if not isinstance(expected_type, list):
        expected_type = [expected_type]

    for et in expected_type:
        if isinstance(obj, et):
            return
    raise SystemExit(f"ERROR: {obj} is not a valid {expected_type}")