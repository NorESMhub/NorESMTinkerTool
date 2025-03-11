# %%
import sys

import pandas as pd


look_for = '3-h-station'

op_col_n = "Operation (\'A\',\'I\',or max)"
freq_col_n = 'Frequency (mon, 3-h) and spatial (e.g. 3h-global, 3h-station, mon-global, mon-region)'
var_col_n = 'Variable name:'


def get_namlist_string(look_for, fincl_n, filename_output_vars):
    df_output = pd.read_csv(filename_output_vars, index_col=0,header=1)
    df_output.index = df_output.reset_index()['Variable name:'].apply(lambda x: str(x).strip("'"))
    df_output_mon_glob = df_output[df_output[freq_col_n].apply(lambda x: look_for in str(x))]
    df_output_mon_glob.loc[:, op_col_n] = df_output_mon_glob[op_col_n].apply(lambda x: str(x).split(',')[fincl_n-1])
    df_output_mon_glob = df_output_mon_glob[
        df_output_mon_glob[f'Keep/reject: {look_for}'].apply(lambda x: (('K' in str(x))) or ('k' in str(x)))]
    df_output_mon_glob.index = df_output_mon_glob.reset_index()[var_col_n].apply(lambda x: x.strip("'"))
    df_output_mon_glob.loc[:, 'namelist_name'] = df_output_mon_glob.index + ':' + df_output_mon_glob[op_col_n]
    namelist_name = df_output_mon_glob['namelist_name'].to_list()
    namelist_str = "fincl" + str(fincl_n) + " = '"
    for i, name in enumerate(namelist_name):
        if len(name)>0:
            namelist_str += name + "','"
        if i%10==0 and (i<len(namelist_name)-1):
            namelist_str = namelist_str[:-1]
            namelist_str = namelist_str + "\n '"
    namelist_str = namelist_str[:-2]
    return namelist_str




if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 0:
        filename_output_vars = 'input_files/output_variables.csv'
    else:
        filename_output_vars = args[0]
    namelist_str = get_namlist_string('mon-global',1,filename_output_vars)
    print(namelist_str)

    namelist_str = get_namlist_string('3-h-station',2,filename_output_vars)
    print(namelist_str)
