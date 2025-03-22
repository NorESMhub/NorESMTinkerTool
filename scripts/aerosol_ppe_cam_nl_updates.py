import argparse as ap
import configparser
from tinkertool.utils.write_out_station_nl_string import write_out_station_nm_string
from tinkertool.utils.write_out_namelist_opt_fincl import get_namlist_string
import pkg_resources
import copy

config_path = pkg_resources.resource_filename('config','default_control_atm.ini')
station_csv = pkg_resources.resource_filename('input_files', 'stations_combined.csv')
fincl_csv = pkg_resources.resource_filename('input_files', 'output_variables.csv')

def read_config(config_file):
    with open(config_file) as f:
        config = configparser.ConfigParser()
        config.read_file(f)
    return copy.copy(config)

def main():
    global config_path
    global station_csv
    global fincl_csv
    parser = ap.ArgumentParser(
        description="Write out fincl namelist from csv station file or from csv fincl file")
    parser.add_argument("--station-data-file","-st", type=str, default=None, 
                        help="Path to the station csv file")
    parser.add_argument("--fincl-data-file","-fi", type=str, default=None, 
                        help="Path to the fincl scv file")
    parser.add_argument("--control-atm-file","-ca", type=str, default=None, 
                        help="Path to the control atm namelist file")
    parser.add_argument("--overwrite-existing-fincl","-o", action="store_true", 
                        help="Overwrite the existing fincl defined in the control atm file")
    parser.add_argument("--output-file","-of", type=str, default="./aerosol_ppe_control_atm.ini",
                        help="Path to the where to write the update control atm file")
    parser.add_argument("--pertape-flags","-pf",nargs='+',type=str, default=['A','I'])
    args = parser.parse_args()

    

    if args.station_data_file and args.fincl_data_file:
        raise ValueError("Either station data file or fincl data file should be provided")
    if args.station_data_file:
        station_data_string = write_out_station_nm_string(args.station_data_file)
    else:
        station_data_string = write_out_station_nm_string(station_csv)
    if args.fincl_data_file:
        namelist_string = get_namlist_string('mon-global',1,args.fincl_data_file,'A')
        station_data_namlist_vars = get_namlist_string('3-h-station',2,args.fincl_data_file,'I')
    else:
        namelist_string = get_namlist_string('mon-global',1,fincl_csv, 'A')
        station_data_namlist_vars = get_namlist_string('3-h-station',2,fincl_csv, 'I')

    if args.control_atm_file:
        config_path = args.control_atm_file
    else:
        config_path = config_path
    config = read_config(config_path)
    nml_variable = namelist_string.split('=')[0].strip()
    station_nml_varialbe = station_data_namlist_vars.split('=')[0].strip()
    nml_from_config = config['camexp'].get(nml_variable, None)
    # Merge namelist_string with name list from control atm file
    for nml_n,nml_v in zip([nml_variable, station_nml_varialbe], [namelist_string, station_data_namlist_vars]):
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
    with open(args.output_file, 'w') as f:
        config.write(f)


if __name__ == '__main__':
    main()