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



def test_generate_paramfile_lhc_no_fates_ctsm(tmp_path:pathlib.Path):
    test_ini = tmp_path / "test_ppe.ini"
    test_paramfile = tmp_path / "test_paramfile.nc"

    ini_content = """
    [test_parameter1]
    esm_component = CAM
    sampling = linear
    ndigits = 4.0
    max = 0.004
    min = 0.5
    default= 0.006


    [test_parameter2]
    esm_component = CAM
    sampling = linear
    ndigits = 2.0
    max = 100
    min = 10
    default= 50


    [test_parameter3]
    esm_component = CAM
    sampling = log
    max = 30
    min= 0.1
    ndigits = 3.0
    default= 5.0
    interdependent_with = None


    [test_parameter4]
    esm_component = CLM
    sampling = linear
    default = 0.025
    scale_fact = 0.5
    ndigits = 4.0
    input_type = CTSM_param_file
    """
    test_ini.write_text(ini_content)

    proc = subprocess.run(
        [sys.executable, "-m", "tinkertool.scripts.generate_paramfile.main",
         '--param-ranges-inpath', str(test_ini),
         '--param-sample-outpath', str(test_paramfile),
         '--nmb-sim', "30",
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
        
    assert defaults_from_file == [0.006, 50.0, 5.0], f"Default values in output file do not match expected defaults: {defaults_from_file}"
    assert n_sims == 31, f"Number of simulations in output file is {n_sims}, expected 30 + 1 (default simulation)."
