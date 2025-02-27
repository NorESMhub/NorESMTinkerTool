import sys

import pandas as pd


def lon_str(x):
    if x>=0:
        return f'{x:.2f}e'

    else:
        return f'{(-x):.2f}w'

def lat_str(x):
    if x>=0:
        return f'{x:.2f}n'
    else:
        return f'{(-x):.2f}s'
 # %%
def write_out_station_nm_string(path_station_file, history_field = 2):
    """
    Write out a string of station names for use in a namelist.

    :param path_station_file:
    :return:
    """
    # %%
    if path_station_file is None:
        path_station_file = 'input_files/stations_combined.csv'
    # %%
    combined_df = pd.read_csv(path_station_file, index_col=0)

    dft = combined_df.copy()
    dft['lon'] = dft['lon'].astype(float)
    dft['lat'] = dft['lat'].astype(float)

    dft['lon_str'] = dft['lon'].apply(lambda x: lon_str(x))
    dft['lat_str'] = dft['lat'].apply(lambda x: lat_str(x))
    
    dft['fincl2lonlat'] =dft.T.apply(lambda x: '%s_%s'%(x['lon_str'],x['lat_str']))
    str_namelist = dft['fincl2lonlat'].to_list()
    str_namelist = "','".join(str_namelist)
    nl_string = f"fincl{history_field:d}lonlat='{str_namelist}'"
    print(nl_string)
    # %%
    return nl_string


if __name__ == '__main__':
    write_out_station_nm_string(*sys.argv[1:])