from tinkertool import NorESMTinkerTool_abspath

try:
    import xarray as xr
except ImportError as e:
    err_msg = "xarray is required for visualization. Please install the 'sampling' extra by running:\n\
cd {}\n\
pip install -e .[sampling]".format(NorESMTinkerTool_abspath)
    raise ImportError(err_msg) from e

try:
    import matplotlib
    # Set non-interactive backend before importing pyplot
    matplotlib.use('Agg')  # Use Anti-Grain Geometry backend (no GUI)
    import seaborn as sns
    import matplotlib.pyplot as plt
except ImportError as e:
    err_msg = "Seaborn and Matplotlib are required for visualization. Please install the 'plotting' extra by running:\n\
cd {}\n\
pip install -e .[plotting]".format(NorESMTinkerTool_abspath)
    raise ImportError(err_msg) from e

from pathlib import Path

def visualize_paramfile(
    paramfile_path: str | Path,
    save_path: str | Path | None = None,
    show: bool = False
):
    """Visualize the paramfile in a pairplot for each dimension.

    Parameters
    ----------
    paramfile_path : str | Path
        path to the parameter file in netCDF format.
    save_path : str | Path, optional
        path to save the plot. If None, saves to same directory as paramfile.
    show : bool, optional
        whether to show the plot (requires GUI). Default False for headless systems.
    """
    paramfile_path = Path(paramfile_path)
    if not paramfile_path.is_file():
        raise FileNotFoundError(f"Parameter file not found: {paramfile_path}")

    # Load the parameter file into a DataFrame
    df = xr.open_dataset(paramfile_path).to_dataframe()

    # plot pairplot
    pairplot = sns.pairplot(df)
    # overlay the highlighted point on every off-diagonal scatter axis
    # TODO: make which point to highlight configurable and optional
    # right now it assumes the point to highlight is the first row
    # which is generally true if exclude_default=False in the paramfile generation.
    # However, this may not always be the case.
    default_row = df.iloc[0]
    vars = list(df.columns)
    for i, yvar in enumerate(vars):
        for j, xvar in enumerate(vars):
            ax = pairplot.axes[i, j]
            if i == j:
                # diagonal: draw a vertical line at the value
                ax.axvline(default_row[yvar], color="red", linewidth=2, zorder=5)
            else:
                # off-diagonal: plot the single highlighted point
                ax.scatter(default_row[xvar], default_row[yvar],
                        color="red", edgecolor="k", s=80, zorder=100)

    # Save or show the plot
    if save_path is None:
        # Default: save to same directory as paramfile
        save_path = paramfile_path.parent.joinpath(f"{paramfile_path.stem}_pairplot.png")
    else:
        save_path = Path(save_path).resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the plot
    pairplot.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Plot saved to: {save_path}")

    # Optionally show (only if GUI available)
    if show:
        try:
            plt.show()
        except Exception as e:
            print(f"Could not show plot (no display available): {e}")
            print(f"Plot has been saved to: {save_path}")

    plt.close()  # Clean up to avoid memory issues

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Visualize parameter file as pairplot")
    parser.add_argument("paramfile", type=Path, help="Path to parameter file (.nc)")
    parser.add_argument("--save", type=Path, help="Path to save plot (default: same dir as paramfile)")
    parser.add_argument("--show", action="store_true", help="Show plot (requires GUI)")

    args = parser.parse_args()

    visualize_paramfile(args.paramfile, args.save, args.show)