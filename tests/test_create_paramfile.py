from tinkertool.utils.make_land_parameterfiles import make_new_ctsm_pamfile
from tinkertool.scripts.generate_paramfile.config import ParameterFileConfig
from tinkertool.scripts.generate_paramfile.generate_paramfile import generate_land_model_param_files
from pathlib import Path
from tinkertool.scripts.generate_paramfile import generate_paramfile
import xarray as xr

def test_create_paramfile_with_ctsm_param_changes(
    sample_ctsm_paramfile: Path,
    sample_parameter_file: Path,
    temp_dir: Path
):
    """Test the make_new_ctsm_pamfile function to ensure it correctly perturbs CTSM parameters."""
    output_ctsm_paramfile = temp_dir / "perturbed_ctsm_params.nc"
    parm_conf = ParameterFileConfig(
    param_ranges_inpath=sample_parameter_file,
    param_sample_outpath=temp_dir / "sample_paramfile.nc",
    tinkertool_output_dir=temp_dir,
    chem_mech_file=None,
    ctsm_default_param_file=sample_ctsm_paramfile,
    nmb_sim=3,
    avoid_scramble=False,
    exclude_default=False,
    log_dir=temp_dir / "logs",
    verbose=2   
    )
    parm_conf = parm_conf.get_checked_and_derived_config()
    assert parm_conf.change_ctsm_params == True
    generate_paramfile(parm_conf)
    assert (temp_dir / "sample_paramfile.nc").exists(), "Sample parameter file was not created."
    assert (temp_dir / "sample_paramfile.raw.nc").exists(), "Raw sample parameter file was not created."
    assert (temp_dir / "paramfile/paramfile_file_sim0.nc").exists(), "Parameter file for simulation 0 was not created."

    ds_raw = xr.open_dataset(parm_conf.param_sample_outpath.with_suffix('.raw.nc'))
    assert 'test_parameter1' in ds_raw.data_vars, "test_parameter1 not found in raw parameter file."
    assert ds_raw['nmb_sim'].size == 4, "Number of simulations in raw parameter file is incorrect."
    assert ds_raw['d_max'].values[0] == 13.0, "Default value for d_max is incorrect in raw parameter file."

def test_create_paramfile_without_ctsm_param_changes(
    sample_parameter_file: Path,
    temp_dir: Path
):
    """Test the generate_paramfile function without CTSM parameter changes."""
    parm_conf = ParameterFileConfig(
        param_ranges_inpath=sample_parameter_file,
        param_sample_outpath=temp_dir / "sample_paramfile.nc",
        tinkertool_output_dir=temp_dir,
        chem_mech_file=None,
        ctsm_default_param_file=None,
        nmb_sim=3,
        avoid_scramble=False,
        exclude_default=True,
        log_dir=temp_dir / "logs",
        verbose=2,   
        params = ['test_parameter1', 'test_parameter2', 'test_parameter3']
    )
    parm_conf = parm_conf.get_checked_and_derived_config()
    assert parm_conf.change_ctsm_params == False
    generate_paramfile(parm_conf)
    assert (temp_dir / "sample_paramfile.nc").exists(), "Sample parameter file was not created."
    assert (temp_dir / "sample_paramfile.raw.nc").exists(), "Raw sample parameter file was not created."

    ds_raw = xr.open_dataset(parm_conf.param_sample_outpath.with_suffix('.raw.nc'))
    assert 'test_parameter1' in ds_raw.data_vars, "test_parameter1 not found in raw parameter file."
    assert ds_raw['nmb_sim'].size == 3, "Number of simulations in raw parameter file is incorrect."

def test_creation_oat(sample_parameter_file: Path, temp_dir: Path):
    output_oat_file = temp_dir / "oat_paramfile.nc"

    parm_conf = ParameterFileConfig(
        param_ranges_inpath=sample_parameter_file,
        param_sample_outpath=output_oat_file,
        tinkertool_output_dir=temp_dir,
        chem_mech_file=None,
        ctsm_default_param_file=None,
        method='oat',
        params=['test_parameter1', 'test_parameter2','test_parameter3', 'test_parameter4'],
        log_dir=temp_dir / "logs",
        verbose=2
    )
    parm_conf = parm_conf.get_checked_and_derived_config()
    assert parm_conf.method == 'oat'
    generate_paramfile(parm_conf)
    assert output_oat_file.exists(), "OAT parameter file was not created."