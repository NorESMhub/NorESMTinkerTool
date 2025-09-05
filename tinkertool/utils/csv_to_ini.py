from pathlib import Path
from typing import Union

import pandas as pd


def df_to_ini(
    df: pd.DataFrame,
    ini_file_path: Union[str, Path],
    section_column: str,
    columns_to_include: Union[str, list, dict, None] = None,
):
    """Convert a DataFrame to an INI file format.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to convert.
    ini_file_path : Union[str, Path]
        The path to the INI file to create.
    section_column : str
        The column name in the DataFrame to use as the section header in the INI file.
    columns_to_include : Union[str, list, dict, None], optional
        The columns to include in the INI file. If None, all columns but the 'section_column'
        will be included as values under the section header.
        String and list options are interpreted as column names.
        If a dictionary, it should be a mapping of column names to "new" attribute names
        used in the INI file. Default is None.
    """

    # Check if the section column exists in the DataFrame
    if section_column not in df.columns:
        raise ValueError(f"Section column '{section_column}' not found in DataFrame.")

    # Determine which columns to include as keys
    if columns_to_include is None:
        section_keys = [col for col in df.columns if col != section_column]
    elif isinstance(columns_to_include, str):
        section_keys = [columns_to_include]
    elif isinstance(columns_to_include, list):
        section_keys = columns_to_include
    elif isinstance(columns_to_include, dict):
        section_keys = list(columns_to_include.keys())
    else:
        raise ValueError("columns_to_include must be None, str, list, or dict.")

    # Prepare DataFrame with selected columns
    ini_df = df[[section_column] + section_keys]

    # Convert ini_file_path to Path
    ini_file_path = Path(ini_file_path)

    # Write the DataFrame to an INI file
    with ini_file_path.open("w") as ini_file:
        for _, row in ini_df.iterrows():
            section_name = str(row[section_column]).strip()
            ini_file.write(f"[{section_name}]\n")
            for col in section_keys:
                if isinstance(columns_to_include, dict):
                    out_col = columns_to_include[col]
                else:
                    out_col = col

                value = row[col]
                if isinstance(value, (list, tuple)):
                    value = ", ".join(map(str, value))
                ini_file.write(f"{out_col} = {value}\n")
            ini_file.write("\n")
