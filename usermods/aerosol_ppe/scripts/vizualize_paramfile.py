from tinkertool.scripts.generate_paramfile.visualize_paramfile import visualize_paramfile
from pathlib import Path


if __name__ == "__main__":
    
    visualize_paramfile(
    '../aerosol_ppe.raw.nc',
    save_path=Path('../output_files', 'figures', 'NorESM3_tuningparameterinfo_PPE_pairplot.png').resolve(),
    )