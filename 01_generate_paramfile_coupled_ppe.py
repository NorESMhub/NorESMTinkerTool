#%%
# --- import modules ---
import xarray as xr
from pathlib import Path

from tinkertool.scripts.generate_paramfile.config import ParameterFileConfig
from tinkertool.scripts.generate_paramfile.generate_paramfile import generate_paramfile

# Perform commands from the script directory pov
script_dir = Path(__file__).parent

#%%
# --- define parameter file configuration ---
parm_conf = ParameterFileConfig(
    param_ranges_inpath=script_dir.joinpath('input_files', 'NorESM3_tuningparameterinfo_PPE.ini').resolve(),
    param_sample_outpath=script_dir.joinpath('input_files', 'NorESM3_tuningparameterinfo_PPE.nc').resolve(),
    chem_mech_file=None,
    ctsm_default_param_file=None,
    fates_default_param_file=None,
    nmb_sim=75,
    avoid_scramble=False,
    exclude_default=False,
    log_dir=script_dir.joinpath('output_files', 'logs'),
    verbose=2
)

#%%
# --- generate parameter file ---
generate_paramfile(config=parm_conf)

with xr.open_dataset(parm_conf.param_sample_outpath.with_suffix('.raw.nc')) as ds:
    ds_string = ds.to_dataframe().to_string()
print("\n", ds_string)

#%%
# --- visualize parameter file ---

visualize_paramfile(
    parm_conf.param_sample_outpath.with_suffix('.raw.nc'),
    save_path=script_dir.joinpath('output_files', 'figures', 'NorESM3_tuningparameterinfo_PPE_pairplot.png').resolve(),
)

# %%
