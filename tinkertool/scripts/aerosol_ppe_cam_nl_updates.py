# -----------------------------------------------------------------------------------
#
# Description
# -----------
#   The main function generates and saves a control atm namelist file
#   containing fincl namelist variables from a csv file containing station data or from a csv file
#   containing fincl data. The script will;
#       - merge the fincl namelist variables with the existing fincl namelist variables in the
#         control atm namelist file.
#       - write out the station data string to the control atm namelist file.
#       - Update the avgflag_pertape variable in the control atm namelist file.
#
# Author
# ------
#   Ove Haugvaldstad, Meteorologisk institutt, Norway
#
# -----------------------------------------------------------------------------------

# ------------------------ #
# --- Import libraries --- #
# ------------------------ #
import argparse
import pkg_resources

from tinkertool.utils.read_files import read_config
from tinkertool.utils.write_out_namelist_opt_fincl import get_namlist_string
from tinkertool.utils.write_out_station_nl_string import write_out_station_nm_string

# ------------------------ #
# --- Global variables --- #
# ------------------------ #
config_path = pkg_resources.resource_filename('config','default_control_atm.ini')
station_csv = pkg_resources.resource_filename('input_files', 'stations_combined.csv')
fincl_csv = pkg_resources.resource_filename('input_files', 'output_variables.csv')

# --------------------- #
# --- Main function --- #
# --------------------- #
def main():
    """Command line interface for writing out fincl namelist from csv station file or from csv fincl file.
    The script generates a fincl namelist string from a csv file containing station data or from a csv file
    containing fincl data.

    Raises
    ------
    ValueError
       If both station data file and fincl data file are provided
    """

    # --- Define global variables
    global config_path
    global station_csv
    global fincl_csv
    width = 40

    # --- Define CLI arguments
    parser = argparse.ArgumentParser(
        description="Write out fincl namelist from csv station file or from csv fincl file")
    parser.add_argument("--station-data-file","-st", type=str, default=None,
                        help="Path to the station csv file")
    parser.add_argument("--fincl-data-file","-fi", type=str, default=None,
                        help="Path to the fincl scv file")
    parser.add_argument("--control-atm-file","-ca", type=str, default=None,
                        help="Path to the control atm namelist file")
    parser.add_argument("--output-file","-of", type=str, default=None,
                        help="Path to the where to write the update control atm file")
    parser.add_argument("--overwrite-existing-fincl", "-o", action="store_true",
                        help="Overwrite the existing fincl defined in the control atm file")
    parser.add_argument("--pertape-flags","-pf",nargs='+',type=str, default=['A','I'])
    parser.add_argument("-v", "--verbose", action="count", default=0,
        help="Increase verbosity level (use -v for more detail)"
    )
    args = parser.parse_args()

    # --- check CLI arguments and handle defaults
    # -- verbose
    verbose = False
    if args.verbose > 0:
        verbose = True
        print("Verbose output enabled")
    # setup control
    if args.station_data_file and args.fincl_data_file:
        raise ValueError("Either station data file or fincl data file should be provided")
    # --station-data-file
    station_data_file = args.station_data_file if args.station_data_file is not None else station_csv
    station_data_string = write_out_station_nm_string(station_data_file)
    if verbose:
        print(f"{'Using station data file'.ljust(width)}: {station_data_file}")
    # --fincl-data-file
    fincl_data_file = args.fincl_data_file if args.fincl_data_file is not None else fincl_csv
    namelist_string = get_namlist_string('mon-global',1,args.fincl_data_file,'A')
    station_data_namlist_vars = get_namlist_string('3-h-station',2,args.fincl_data_file,'I')
    if verbose:
        print(f"{'Using fincl data file'.ljust(width)}: {fincl_data_file}")
    # -- control-atm-file
    config_path = args.control_atm_file if args.control_atm_file is not None else config_path
    config = read_config(config_path)
    if verbose:
        print(f"{'Using control atm file'.ljust(width)}: {config_path}")
    # -- output-file
    output_file = args.output_file if args.output_file is not None else "./aerosol_ppe_control_atm.ini"
    if verbose:
        print(f"{'Using output file'.ljust(width)}: {output_file}")

    nml_variable = namelist_string.split('=')[0].strip()
    station_nml_varialbe = station_data_namlist_vars.split('=')[0].strip()
    nml_from_config = config['camexp'].get(nml_variable, None)

    # Merge namelist_string with name list from control atm file
    for nml_n, nml_v in zip([nml_variable, station_nml_varialbe], [namelist_string, station_data_namlist_vars]):
        nml_from_config = config['camexp'].get(nml_n, None)
        if nml_from_config is not None and args.overwrite_existing_fincl == False:
            nml_config_vars = nml_from_config.split('\n')
            namelist_string_vars = nml_v.split('=')[1].strip().split('\n')
            # merge the two lists ensuring no duplicates
            namelist_string_vars = list(set(nml_config_vars + namelist_string_vars))
            # sort alphabetically
        else:
            namelist_string_vars = nml_v
            namelist_string_vars = namelist_string_vars.split('=')[1].strip().split('\n')
        namelist_string_vars.sort()
            # updated nml to config
        config['camexp'][nml_n] = ('\n').join(namelist_string_vars)
        # write the station data string to the control atm file

    station_variable_name_str = station_data_string.split('=')[0].strip()
    station_variables_str = station_data_string.split('=')[1].strip()
    config['camexp'][station_variable_name_str] = station_variables_str
    # Write update control atm file
    config['camexp']['avgflag_pertape'] = ",".join(args.pertape_flags)

    with open(output_file, 'w') as out_file:
        config.write(out_file)


if __name__ == '__main__':
    main()