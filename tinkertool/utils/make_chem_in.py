import argparse
from pathlib import Path

from tinkertool.utils.read_files import read_config


def generate_chem_in_ppe(
    scale_factor: float,
    input_file: str,
    outfolder_base: str,
    outfolder_name: str,
    verbose: bool = False,
) -> str:
    """Generate a chemistry namelist file for a given scale factor and input file.

    Parameters:
    -----------
    scale_factor : float
        The scale factor to use for the chemistry file.
    input_file : str
        The input file to use for the chemistry file.
    outfolder_base : str
        The base folder to use for the output files.
    outfolder_name : str
        The name of the folder to use for the output files.
    verbose : bool, optional
        If True, print verbose output. Default False.

    Returns
    -------
    str
        The path to the generated chemistry file.
    """
    # handle input arguments and defaults
    scale_factor = float(scale_factor)
    input_file = Path(input_file).resolve()

    outfolder = Path(outfolder_base).joinpath(outfolder_name).resolve()
    if not outfolder.exists():
        outfolder.mkdir(parents=True)
    outputfile = outfolder.joinpath(f"chem_mech_scale_{scale_factor:.3f}.in")
    if verbose:
        print(
            "creating chem_mech file for scale_factor",
            scale_factor,
            " in\n",
            outputfile,
        )

    with open(input_file, "r") as infile:
        infile_lines = infile.readlines()

    with open(outputfile, "w") as outfile:
        for line in infile_lines:
            replace = False
            if "monoterp" in line or "isoprene" in line:
                if "->" in line:
                    if "+" in line:
                        if ";" in line:
                            replace = True
            if replace:

                yld = line.split("->")[1].split("*")[0].strip()
                new_yld = float(yld) * scale_factor
                new_yld = f"{new_yld:.3f}"
                replacement_text = line.replace(yld, new_yld)
                if verbose:
                    print(f"Replacing \n {line} \n with \n {replacement_text}")
                outfile.write(replacement_text)

            else:
                outfile.write(line)

    return str(outputfile)


def check_if_chem_mech_is_perterbed(param_ranges_inpath: str) -> bool:
    """Check if the chemistry mechanism is perturbed. The check is
    performed by looking for specific section headers defined in
    chem_mech_variable_flags in the parameter ranges file.

    Parameters
    ----------
    param_ranges_inpath : str
        The path to the parameter ranges file.

    Returns
    -------
    bool
        True if the chemistry mechanism is perturbed, False otherwise.
    """
    chem_mech_variable_flags = ["SOA_y_scale_chem_mech_in"]

    param_ranges = read_config(Path(param_ranges_inpath).resolve())

    for param in param_ranges.sections():
        if param in chem_mech_variable_flags:
            return True
    return False


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate a chemistry namelist file for a given scale factor and input file."
    )
    parser.add_argument(
        "scale_factor",
        type=float,
        help="The scale factor to use for the chemistry file.",
    )
    parser.add_argument(
        "--outfolder_base",
        type=str,
        default=None,
        help="The base folder to use for the output files. Default is the current working directory.",
    )
    parser.add_argument(
        "--outfolder_name",
        type=str,
        default=None,
        help="The name of the folder to use for the output files. Default is 'chem_mech_files'.",
    )
    parser.add_argument(
        "--input_file",
        type=str,
        default=None,
        help="The input file to use for the chemistry file. Default is 'config/chem_mech_default.in'.",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="If set, print verbose output."
    )
    args = parser.parse_args()

    generate_chem_in_ppe(
        scale_factor=args.scale_factor,
        outfolder_base=args.outfolder_base,
        outfolder_name=args.outfolder_name,
        input_file=args.input_file,
        verbose=args.verbose,
    )
