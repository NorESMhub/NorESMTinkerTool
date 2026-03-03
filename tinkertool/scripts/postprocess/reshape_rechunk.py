import logging
import pandas as pd
import xarray as xr
from pathlib import Path
from typing import Optional

from tinkertool.scripts.postprocess.config import (
    ReshapeRechunkConfig,
    CheckedReshapeRechunkConfig,
)
from tinkertool.utils.custom_logging import setup_logging, log_info_detailed

# Dimension names recognised as vertical levels in CESM/NorESM output
VERTICAL_DIMS: frozenset[str] = frozenset({
    'lev', 'ilev',          # atmosphere (CAM)
    'z_t', 'z_w', 'z_w_top', 'z_w_bot',  # ocean (BLOM / POP)
    'depth',                # generic
    'plev', 'lev_p',        # pressure-interpolated levels
})


def _find_member_dirs(input_dir: Path) -> list[Path]:
    """Return sorted list of all immediate subdirectories of *input_dir*."""
    dirs = sorted([d for d in input_dir.iterdir() if d.is_dir()])
    if not dirs:
        raise ValueError(
            f"No subdirectories found in '{input_dir}'. "
            "Each ensemble member must be in its own subdirectory."
        )
    return dirs


def _open_member_dataset(member_dir: Path, file_pattern: str) -> xr.Dataset:
    """Open all NetCDF files matching *file_pattern* inside *member_dir* as a single dataset."""
    files = sorted(member_dir.glob(file_pattern))
    if not files:
        raise FileNotFoundError(
            f"No files matching '{file_pattern}' found in '{member_dir}'."
        )
    return xr.open_mfdataset(
        files,
        combine='by_coords',
        chunks={},           # open with dask chunks (auto-sized to one chunk per file)
        data_vars='minimal', # only load data variables that differ across files
        coords='minimal',
        compat='override',
    )


def _build_chunk_dict(
    dims: tuple[str, ...],
    sizes: dict[str, int],
    time_chunk: int,
    lev_chunk: int,
) -> dict[str, int]:
    """Build a dask chunk dictionary for a DataArray.

    * ``time``            → *time_chunk*
    * vertical dimension  → *lev_chunk* (or full size when *lev_chunk* == -1)
    * all other dims      → full size (single chunk)
    """
    chunks: dict[str, int] = {}
    for dim in dims:
        if dim == 'time':
            chunks[dim] = time_chunk
        elif dim in VERTICAL_DIMS:
            chunks[dim] = sizes[dim] if lev_chunk == -1 else lev_chunk
        else:
            chunks[dim] = sizes[dim]
    return chunks


def _write_variable(
    da: xr.DataArray,
    var: str,
    output_dir: Path,
    output_format: str,
    chunks: dict[str, int],
) -> None:
    """Write a single rechunked DataArray to disk in the requested format(s)."""
    ds = da.to_dataset(name=var)

    if output_format in ('zarr', 'both'):
        zarr_path = output_dir / f"{var}.zarr"
        log_info_detailed('tinkertool_log', f"  Writing Zarr store → {zarr_path}")
        ds.to_zarr(zarr_path, mode='w')

    if output_format in ('netcdf4', 'both'):
        nc_path = output_dir / f"{var}.nc"
        log_info_detailed('tinkertool_log', f"  Writing NetCDF4    → {nc_path}")
        # Build encoding: chunksizes must follow the DataArray dimension order
        chunksizes = tuple(chunks[d] for d in da.dims)
        encoding = {var: {'chunksizes': chunksizes, 'zlib': True, 'complevel': 4}}
        ds.to_netcdf(nc_path, encoding=encoding, engine='netcdf4')


def reshape_and_rechunk(config: ReshapeRechunkConfig) -> None:
    """Reshape and rechunk PPE output into one-file-per-variable stores.

    For each variable found in the ensemble members' output:

    * Concatenates all members along a new ``ens_member`` dimension.
    * Rechunks 2-D variables in time only; 3-D variables in time **and** the
      vertical level dimension.
    * Writes one ``<variable>.zarr`` / ``<variable>.nc`` file per variable to
      *config.output_dir*.

    Parameters
    ----------
    config:
        A :class:`ReshapeRechunkConfig` (or already-checked
        :class:`CheckedReshapeRechunkConfig`) instance.
    """
    checked_config: CheckedReshapeRechunkConfig = config.get_checked_and_derived_config()

    if not logging.getLogger('tinkertool_log').handlers:
        setup_logging(
            checked_config.verbose,
            checked_config.log_file,
            checked_config.log_mode,
            'tinkertool_log',
        )

    logging.info("> Starting PPE reshape and rechunk")
    logging.info(f"  input_dir     : {checked_config.input_dir}")
    logging.info(f"  output_dir    : {checked_config.output_dir}")
    logging.info(f"  output_format : {checked_config.output_format}")
    logging.info(f"  time_chunk    : {checked_config.time_chunk}")
    logging.info(
        f"  lev_chunk     : "
        f"{'full dimension' if checked_config.lev_chunk == -1 else checked_config.lev_chunk}"
    )
    logging.info(f"  file_pattern  : {checked_config.file_pattern}")

    # ------------------------------------------------------------------
    # 1. Discover ensemble member directories
    # ------------------------------------------------------------------
    member_dirs = _find_member_dirs(checked_config.input_dir)
    member_names = [d.name for d in member_dirs]
    logging.info(f"  Found {len(member_dirs)} member directories: {member_names}")

    # ------------------------------------------------------------------
    # 2. Open per-member datasets (lazy, dask-backed)
    # ------------------------------------------------------------------
    member_datasets: list[xr.Dataset] = []
    for member_dir in member_dirs:
        logging.info(f"  Opening member: {member_dir.name}")
        try:
            ds = _open_member_dataset(member_dir, checked_config.file_pattern)
            member_datasets.append(ds)
        except FileNotFoundError as exc:
            logging.error(str(exc))
            raise

    # ------------------------------------------------------------------
    # 3. Determine the set of variables to process
    # ------------------------------------------------------------------
    all_vars: set[str] = set()
    for ds in member_datasets:
        all_vars.update(ds.data_vars)

    if checked_config.variables_list is not None:
        unknown = set(checked_config.variables_list) - all_vars
        if unknown:
            logging.warning(
                f"  The following requested variables were not found in any member "
                f"and will be skipped: {sorted(unknown)}"
            )
        all_vars = all_vars & set(checked_config.variables_list)

    variables_to_process = sorted(all_vars)
    logging.info(f"  Variables to process ({len(variables_to_process)}): {variables_to_process}")

    # ------------------------------------------------------------------
    # 4. Process each variable
    # ------------------------------------------------------------------
    ens_index = pd.Index(member_names, name='ens_member')

    for var in variables_to_process:
        logging.info(f"> Processing variable: {var}")

        # Collect per-member DataArrays; skip members missing this variable
        arrays: list[xr.DataArray] = []
        valid_member_names: list[str] = []
        for name, ds in zip(member_names, member_datasets):
            if var not in ds:
                logging.warning(
                    f"  Variable '{var}' not found in member '{name}'; skipping that member."
                )
                continue
            arrays.append(ds[var])
            valid_member_names.append(name)

        if not arrays:
            logging.warning(f"  No members contain variable '{var}'; skipping.")
            continue

        if len(arrays) < len(member_names):
            # Rebuild index for the subset of members that have this variable
            ens_index_var = pd.Index(valid_member_names, name='ens_member')
        else:
            ens_index_var = ens_index

        # Concatenate along the new ens_member dimension
        combined: xr.DataArray = xr.concat(arrays, dim=ens_index_var)

        # Determine chunking
        has_vertical = bool(set(combined.dims) & VERTICAL_DIMS)
        log_info_detailed(
            'tinkertool_log',
            f"  '{var}' dims={list(combined.dims)}, "
            f"{'3-D (time+lev chunked)' if has_vertical else '2-D (time chunked)'}"
        )

        chunks = _build_chunk_dict(
            combined.dims,
            dict(combined.sizes),
            checked_config.time_chunk,
            checked_config.lev_chunk,
        )
        combined = combined.chunk(chunks)

        # Write output
        _write_variable(
            combined,
            var,
            checked_config.output_dir,
            checked_config.output_format,
            chunks,
        )
        logging.info(f"  Done: {var}")

    # Close all open datasets
    for ds in member_datasets:
        ds.close()

    logging.info("> PPE reshape and rechunk complete.")
    logging.info(f"  Output written to: {checked_config.output_dir}")
