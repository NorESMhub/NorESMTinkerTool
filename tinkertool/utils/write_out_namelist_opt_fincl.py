# %%
import sys

import pandas as pd

look_for = "3-h-station"

op_col_n = "Operation ('A','I',or max)"
freq_col_n = "Frequency (mon, 3-h) and spatial (e.g. 3h-global, 3h-station, mon-global, mon-region)"
var_col_n = "Variable name:"


def get_namlist_string(look_for, 
                       fincl_n, 
                       filename_output_vars, 
                       operation,
                       category_exclude=None,
                       category_include=None):
    df_output = pd.read_csv(filename_output_vars, index_col=0, header=1)
    df_output = df_output.rename(columns={
        'category': 'category',
       'Frequency (mon, 3-h) and spatial (e.g. 3h-global, 3h-station, mon-global, mon-region)':'Freq',
       'Operation (A,I,or max)': 'opflag',
       'Variable name:': 'varname',
       'Keep/reject: mon-global': 'mon-global(k/r)',
       'Keep/reject: 3-h-station':'3-h-station(k/r)', 
       'Dimensions (2D,3D)': '2D_3D', 
       'comment': 'comment',
       'nl history flagg': 'nl_history_flagg'
    }
    )

    df_output_mon_glob = df_output[
        df_output['Freq'].apply(lambda x: look_for in str(x))
    ]
    temp = df_output_mon_glob["opflag"].str.contains("A", na=False).copy()
    df_output_mon_glob['A'] = temp
    temp = df_output_mon_glob["opflag"].str.contains("I", na=False).copy()
    df_output_mon_glob['I'] = temp
    df_output_mon_glob = df_output_mon_glob[
        df_output_mon_glob[f"{look_for}(k/r)"].apply(
            lambda x: (("K" in str(x))) or ("k" in str(x))
        )
    ]
    if category_include is not None:
        df_output_mon_glob = df_output_mon_glob.loc[df_output_mon_glob['category'].apply(lambda x: x in category_include)]
    if category_exclude is not None:
        df_output_mon_glob = df_output_mon_glob.loc[~df_output_mon_glob['category'].apply(lambda x: x in category_exclude)]
    # select where "Operation ('A','I',or max)" is equal to operation
    operation_filter = df_output_mon_glob[operation] == True
    df_output_mon_glob = df_output_mon_glob[operation_filter]
    df_output_mon_glob.loc[:, "namelist_name"] = df_output_mon_glob.index
    namelist_name = df_output_mon_glob["namelist_name"].to_list()
    namelist_str = "fincl" + str(fincl_n) + " = "
    for i, name in enumerate(namelist_name):
        namelist_str += f"{name}\n"
    namelist_str = namelist_str[:-2]
    return namelist_str


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 0:
        filename_output_vars = "input_files/output_variables.csv"
    else:
        filename_output_vars = args[0]
    namelist_str = get_namlist_string("mon-global", 1, filename_output_vars, "A")
    print(namelist_str)

    namelist_str = get_namlist_string("3-h-station", 2, filename_output_vars, "I")
    print(namelist_str)
