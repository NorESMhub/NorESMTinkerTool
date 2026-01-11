"""Pytest configuration and setup of shared fixtures."""

import pytest
from pathlib import Path
from typing import Generator
from tempfile import TemporaryDirectory
import xarray as xr
import numpy as np

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    with TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_parameter_file(temp_dir: Path) -> Path:
    parameter_ranges_ini_content = """
    [test_parameter1]
    esm_component = CAM
    sampling = linear
    ndigits = 5
    max = 0.005
    min = 0.002
    default= 0.0034

    [test_parameter2]
    esm_component = CAM
    sampling = linear
    ndigits = 2
    max = 100
    min = 10
    default= 50

    [test_parameter3]
    esm_component = CAM
    sampling = log
    max = 30
    min= 0.1
    ndigits = 3
    default= 5.0
    interdependent_with = None

    [test_parameter4]
    esm_component = CLM
    sampling = linear
    default = 0.025
    scale_fact = 0.5
    ndigits = 4

    [d_max]
    esm_component = CLM
    sampling = linear
    ndigits = 2
    max = 20.0
    min = 5.0
    default= 13.0
    input_type = CTSM_param_file

    [frac_sat_soil_dsl_init]
    esm_component = CLM
    sampling = linear
    ndigits = 3
    max = 1.0
    min = 0.0
    default= 0.5
    input_type = CTSM_param_file
    """
    parameter_file_path = temp_dir / "test_ppe.ini"
    parameter_file_path.write_text(parameter_ranges_ini_content)
    return parameter_file_path


@pytest.fixture
def sample_usr_nl_ini(temp_dir: Path) -> Path:
    usr_nl_cam_sample_content = """
    [oslo_ctl_nl]
    use_aerocom = .false.

    [cam_history_nl]
    interpolate_nlat   = 96
    interpolate_nlon   = 144
    interpolate_output = .true.

    [phys_ctl_nl]
    history_aerosol = .false.

    [zmconv_nl]
    zmconv_c0_lnd   = 0.0075D0
    zmconv_ke       = 5.0E-6
    zmconv_ke_lnd   = 1.0E-5
    """
    usr_nl_ini_path = temp_dir / "control_cam_test.ini"
    usr_nl_ini_path.write_text(usr_nl_cam_sample_content)
    return usr_nl_ini_path

@pytest.fixture
def sample_ctsm_paramfile(temp_dir: Path) -> Path:
    """Create a sample CTSM parameter file for testing."""
    ds = xr.Dataset(data_vars={'d_max': np.array(13.0), 
                               'frac_sat_soil_dsl_init': np.array(0.5),
                               })
    paramfile_path = temp_dir / "ctsm_paramfile.nc"
    ds.to_netcdf(paramfile_path)
    return paramfile_path