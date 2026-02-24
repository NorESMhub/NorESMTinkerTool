import numpy as np
import pytest

from tinkertool.scripts.generate_paramfile.main import main
from importlib import metadata
import sys
import subprocess

import pathlib


import xarray as xr


@pytest.mark.parametrize("command", [["--version"], ["-v"]])
def test_version(command):

    proc = subprocess.run(
        [sys.executable, "-m", "tinkertool.scripts.generate_paramfile.main", *command],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    assert proc.returncode == 0
    assert "tinkertool" in proc.stdout
    assert metadata.version("tinkertool") in proc.stdout


def test_generate_paramfile_lhc_no_fates_ctsm(temp_dir:pathlib.Path, sample_parameter_file:pathlib.Path):
    
    test_paramfile = temp_dir / "test_paramfile.nc"

    test_ini = sample_parameter_file
    proc = subprocess.run(
        [sys.executable, "-m", "tinkertool.scripts.generate_paramfile.main",
         '--param-ranges-inpath', str(test_ini),
         '--param-sample-outpath', str(test_paramfile),
         '--nmb-sim', "30",
         '--log-mode', "o",
         '--params', "test_parameter1",  "test_parameter2", "test_parameter3"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output_file = test_paramfile
    assert proc.returncode == 0, f"Process failed with output: {proc.stdout}"
    assert output_file.exists(), "Parameter file was not created."
    with xr.open_dataset(output_file) as ds:
        param_names_in_ncfile = list(ds.data_vars.keys())
        param_names_in_ini = ["test_parameter1", "test_parameter2", "test_parameter3"]
        assert set(param_names_in_ncfile) == set(param_names_in_ini), "Parameter names in output file do not match those in input ini file."
        # check that length of parameter arrays are correct
        n_sims = len(ds['nmb_sim'])

        check_defaults = ds.sel(nmb_sim=0)
        defaults_from_file = [float(check_defaults['test_parameter1'].values),
                                float(check_defaults['test_parameter2'].values),
                                float(check_defaults['test_parameter3'].values)]
        
    assert defaults_from_file == [0.0034, 50.0, 5.0], f"Default values in output file do not match expected defaults: {defaults_from_file}"
    assert n_sims == 31, f"Number of simulations in output file is {n_sims}, expected 30 + 1 (default simulation)."


def test_generate_paramfile_oat_no_fates_ctsm(temp_dir:pathlib.Path, sample_parameter_file:pathlib.Path):
    
    test_paramfile = temp_dir / "test_paramfile.nc"

    test_ini = sample_parameter_file
    proc = subprocess.run(
        [sys.executable, "-m", "tinkertool.scripts.generate_paramfile.main",
         '--param-ranges-inpath', str(test_ini),
         '--param-sample-outpath', str(test_paramfile),
         '--log-mode', "o",
         '--params', "test_parameter1",  "test_parameter2", "test_parameter3",
         '--method', "oat"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output_file = test_paramfile
    assert proc.returncode == 0, f"Process failed with output: {proc.stdout}"
    assert output_file.exists(), "Parameter file was not created."