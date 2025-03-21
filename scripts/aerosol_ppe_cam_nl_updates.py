import argparse as ap
import configparser
from tinkertool.utils.write_out_station_nl_string import write_out_station_nm_string
from tinkertool.utils.write_out_namelist_opt_fincl import get_namlist_string
import pkg_resources
import copy

config_path = pkg_resources.resource_filename('config','default_control_atm.ini')
station_csv = pkg_resources.resource_filename(__name__, '../input_files/stations_combined.csv')
fincl_csv = pkg_resources.resource_filename(__name__, '../input_files/output_variables.csv')

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
    args = parser.parse_args()

    

    if args.station_data_file and args.fincl_data_file:
        raise ValueError("Either station data file or fincl data file should be provided")
    if args.station_data_file:
        station_data_string = write_out_station_nm_string(args.station_data_file)
    else:
        station_data_string = write_out_station_nm_string(station_csv)
    if args.fincl_data_file:
        namelist_string = get_namlist_string('mon-global',1,args.fincl_data_file,'A')
    else:
        namelist_string = get_namlist_string('mon-global',1,fincl_csv, 'A')

    if args.control_atm_file:
        config_path = args.control_atm_file
    else:
        config_path = config_path
    config = read_config(config_path)
    
    import IPython; IPython.embed()


if __name__ == '__main__':
    main()