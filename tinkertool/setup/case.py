# ------------------------ #
# --- Import libraries --- #
# ------------------------ #
import os
import shutil
import subprocess
from pathlib import Path
from itertools import islice
# %%
try:
    import CIME
    import CIME.utils
    CIME.utils.check_minimum_python_version(3, 8)
    CIME.utils.stop_buffering_output()
    import CIME.build as build
    from CIME.case import Case
    from CIME.utils import safe_copy
    from CIME.locked_files import lock_file, unlock_file
except ImportError:
    print("ERROR: CIME not found, update CESMROOT environment variable")
    raise SystemExit
try:
    import standard_script_setup
except ImportError:
    print("ERROR: default_simulation_setup.py not found (Part of CIME)")
    raise SystemExit


from tinkertool.setup.namelist import setup_usr_nlstring

# ------------------------ #
# --- Helper functions --- #
# ------------------------ #
def write_user_nl_file(
    caseroot:       str,
    usernlfile:     str,
    user_nl_str:    str,
    verbose:        bool = True
) -> None:
    """write user_nl string to file

    Parameters
    ----------
    caseroot : str
        root directory of the case
    usernlfile : str
        name of the user_nl file, e.g. user_nl_cam, user_nl_clm ...
    user_nl_str : str
        string to be written to the user_nl file
    verbose : bool
        verbose output
    """
    user_nl_file = os.path.join(caseroot,usernlfile)
    if verbose:
        print("...Writing to user_nl file: ", usernlfile)
    with open(user_nl_file, "a") as funl:
        funl.write(user_nl_str)


def _per_run_case_updates(case: CIME.case,
                          paramdict: dict,
                          componentdict: dict,
                          ens_idx: str,
                          path_base_input:str ='',
                          keepexe: bool=False,
                          lifeCycleMedianRadius=None,
                          lifeCycleSigma=None):
    """
    Update and submit the new cloned case, setting namelist parameters according to paramdict

    Parameters
    ----------
    case : CIME.case
        The case object to be updated
    paramdict : dict
        Dictionary of namelist parameters to be updated
    componentdict : dict
        Dictionary of component names for the parameters
    ens_idx : str
        The ensemble index for the new case
    """
    print(">>>>> BUILDING CLONE CASE...")
    caseroot = case.get_value("CASEROOT")
    basecasename = os.path.basename(caseroot)
    unlock_file("env_case.xml",caseroot=caseroot)
    casename = f"{basecasename}{ens_idx}"
    case.set_value("CASE",casename)
    rundir = case.get_value("RUNDIR")
    rundir = os.path.dirname(rundir)
    rundir = f"{rundir}/run.{ens_idx.split('.')[-1]}"
    case.set_value("RUNDIR",rundir)
    # smb++ extract the chem_mech_in_file
    chem_mech_file = None
    if 'chem_mech_in' in paramdict.keys():
        chem_mech_file = Path(path_base_input)/paramdict['chem_mech_in']
        del paramdict['chem_mech_in']
        del componentdict['chem_mech_in']
    case.flush()
    lock_file("env_case.xml",caseroot=caseroot)
    print("...Casename is {}".format(casename))
    print("...Caseroot is {}".format(caseroot))
    print("...Rundir is {}".format(rundir))

    # --- Add user_nl updates for each run
    # find all comonents that we are editing
    components = list(set(componentdict.values()))

    paramLinesDict = {component: [] for component in components}
    print('ensemble_index')
    print(ens_idx.split('.')[-1])

    for var in paramdict.keys():
        paramLines = paramLinesDict[componentdict[var]]
        if var.startswith('lifeCycleNumberMedianRadius'):
            lifeCycleNumber = int(var.split('_')[-1])
            if lifeCycleMedianRadius is None:
                raise ValueError('A default lifeCylceList has to be specified in default_simulation_setup.ini')
            lifeCylceList = lifeCycleMedianRadius.split(',')
            lifeCylceList[lifeCycleNumber] = "{:.1E}".format(paramdict[var]).replace('E', 'D').replace('+', '')

            paramLines.append("oslo_aero_lifecyclenumbermedianradius = "+','.join(lifeCylceList)+"\n")
        elif var.startswith("lifeCycleSigma"):
            lifeCycleNumber = int(var.split('_')[-1])
            if lifeCycleSigma is None:
                raise ValueError('A default lifeCylceList has to be specified in default_simulation_setup.ini')
            lifeCylceList = lifeCycleSigma.split(',')
            lifeCylceList[lifeCycleNumber] = "{:.1E}".format(paramdict[var]).replace('E', 'D').replace('+', '')
            paramLines.append("oslo_aero_lifecyclesigma = "+','.join(lifeCylceList)+"\n")
        else:
            paramLines.append("{} = {}\n".format(var,paramdict[var]))

    for component in components:
        paramLines = paramLinesDict[component]
        if len(paramLines) > 0:
            usernlfile = os.path.join(caseroot, f"user_nl_{component}")
            with open(usernlfile, "a") as file:
                file.writelines(paramLines)

    if chem_mech_file is not None:
        comm = 'cp {} {}'.format(chem_mech_file, caseroot+'/')
        subprocess.run(comm, shell=True)
        unlock_file("env_build.xml",caseroot=caseroot)
        value = case.get_value("CAM_CONFIG_OPTS", resolved=False)
        case.set_value("CAM_CONFIG_OPTS", f"{value} --usr_mech_infile {caseroot}/{chem_mech_file.name}")
        case.flush()
        lock_file("env_build.xml",caseroot=caseroot)

    print(">> Clone {} case_setup".format(ens_idx))
    case.case_setup()
    print(">> Clone {} create_namelists".format(ens_idx))
    case.create_namelists()
    if keepexe == False:
        print(">> Clone {} build".format(ens_idx))
        build.case_build(caseroot, case=case)

def build_base_case(
    baseroot:                   str,
    basecasename:               str,
    overwrite:                  bool,
    case_settings:              dict,
    env_run_settings:           dict,
    env_build_settings:         dict,
    basecase_startval:          str,
    namelist_collection_dict:   dict,
    cesmroot:                   str = os.environ.get('CESMROOT'),
    verbose:                    bool = True
) -> str:
    """
    Create and build the base case that all PPE cases are cloned from

    Parameters
    ----------
    baseroot : str
        The base directory for the cases
    basecasename : str
        The base case name
    overwrite : bool
        Overwrite existing cases
    case_settings : dict
        Dictionary of case settings
    env_run_settings : dict
        Dictionary of environment run settings
    basecase_startval : str
        The base case start value
    namelist_collection_dict : dict
        Dictionary of namelist collections for the different components
    cesmroot : str
        The CESM root directory, default is CESMROOT environment variable
    verbose : bool
        Verbose output, default is True

    Returns
    -------
    str
        The root directory of the base case
    """
    if verbose:
        print(">>>>> BUILDING BASE CASE...")
    caseroot = os.path.join(baseroot, basecasename+'.' + basecase_startval)
    if overwrite and os.path.isdir(caseroot):
        shutil.rmtree(caseroot)
    with Case(caseroot, read_only=False) as case:
        if not os.path.isdir(caseroot):

            # create the case using the case_settings
            case.create(
                casename=os.path.basename(caseroot),
                srcroot=cesmroot,
                compset_name=case_settings.pop("compset"),
                grid_name=case_settings.pop("res"),
                machine_name=case_settings.pop("mach"),
                walltime=case_settings.pop("walltime"),
                project=case_settings.pop("project"),
                driver="mct",
                run_unsupported=True,
                answer="r",
                **case_settings
            )

            # set the case environment variables
            # first using the case's own values
            # then using the values from the env_run_settings, first required ones, then iterate over the remaining
            # then using the values from the env_build_settings
            case.set_value("EXEROOT", case.get_value("EXEROOT", resolved=True))
            case.set_value("RUNDIR", case.get_value("RUNDIR", resolved=True)+basecase_startval)

            case.set_value("RUN_TYPE", env_run_settings.pop("RUN_TYPE"))
            if env_run_settings.get("GET_REFCASE") is not None:
                case.set_value("GET_REFCASE", env_run_settings.pop("GET_REFCASE"))
            if env_run_settings.get("RUN_REFCASE") is not None:
                case.set_value("RUN_REFCASE", env_run_settings.pop('RUN_REFCASE'))
            if any(env_run_settings.get(key) is not None for key in ['RUN_REFDIR', 'RUN_REFDATE']):
                case.set_value("RUN_REFDIR", env_run_settings.pop("RUN_REFDIR"))
                case.set_value("RUN_REFDATE", env_run_settings.pop("RUN_REFDATE"))

            case.set_value("STOP_OPTION",env_run_settings.pop("STOP_OPTION"))
            case.set_value("STOP_N",env_run_settings.pop("STOP_N"))
            case.set_value("RUN_STARTDATE",env_run_settings.pop("RUN_STARTDATE"))

            if any(env_run_settings.get(key) is not None for key in ['REST_N', 'REST_OPTION']):
                case.set_value("REST_OPTION", env_run_settings.pop("REST_OPTION"))
                case.set_value("REST_N", env_run_settings.pop("REST_N"))

            if env_build_settings.get("CALENDAR") is not None:
                case.set_value("CALENDAR", env_build_settings.pop("CALENDAR"))

            case.set_value("DEBUG", env_build_settings.pop("DEBUG", "FALSE"))
            if env_run_settings.get('CAM_CONFIG_OPTS') is not None:
                if env_run_settings.get('cam_onopts'):
                    Warning.warning(
                        "Both 'CAM_CONFIG_OPTS' and 'cam_onopts' were provided. "
                        "'CAM_CONFIG_OPTS' will overwrite all previous options including 'cam_onopts'."
                    )
                case.set_value('CAM_CONFIG_OPTS', env_run_settings.pop('CAM_CONFIG_OPTS'))
            elif env_run_settings.get('cam_onopts') is not None:
                current_opts = case.get_value('CAM_CONFIG_OPTS', resolved=True)
                new_opts = f"{current_opts} {env_run_settings.pop('cam_onopts')}".strip()
                case.set_value('CAM_CONFIG_OPTS', new_opts)

            for env_dict, env_dict_name in zip([env_run_settings, env_build_settings], ['env_run_settings', 'env_build_settings']):
                for key in env_dict.keys():
                    try:
                        case.set_value(key, env_dict[key])
                    except Exception as exception:
                        print(f"WARNING: {key} not set in {env_dict_name}: {exception}")
                        continue

        if verbose:
            print(">> base case_setup...")
        case.case_setup()

        if verbose:
            print(">> base case write user_nl files...")

        # write user_nl files
        for nl in namelist_collection_dict:
            user_nl_str = setup_usr_nlstring(namelist_collection_dict[nl])
            write_user_nl_file(caseroot, f"user_{nl}", user_nl_str)

        if verbose:
            print(">> base case_build...")
        build.case_build(caseroot, case=case)

        return caseroot


def clone_base_case(baseroot: str,
                    basecaseroot: str,
                    overwrite: bool,
                    paramdict: dict,
                    componentdict: dict,
                    ensemble_idx: str,
                    path_base_input: str='',
                    keepexe: bool=False,
                    **kwargs):
    """
    Clone the base case and update the namelist parameters

    Parameters
    ----------
    baseroot : str
        The base directory for the cases
    basecaseroot : str
        The base case root directory
    overwrite : bool
        Overwrite existing cases
    paramdict : dict
        Dictionary of namelist parameters to be updated
    componentdict : dict
        Dictionary of component names for the parameters
    ensemble_idx : str
        The ensemble index for the new case
    path_base_input : str
        The path to the base input files
    keepexe : bool
        Keep the executable files
    **kwargs : dict
        Additional keyword arguments to be passed to the case updates

    """

    print(">>>>> CLONING BASE CASE...")
    cloneroot = os.path.join(baseroot,ensemble_idx)

    print(f"member_string= {ensemble_idx}")
    if overwrite and os.path.isdir(cloneroot):
        shutil.rmtree(cloneroot)
    if not os.path.isdir(cloneroot):
        with Case(basecaseroot, read_only=False) as clone:
            clone.create_clone(cloneroot, keepexe=keepexe)
    with Case(cloneroot, read_only=False) as case:
        _per_run_case_updates(
            case=case,
            paramdict=paramdict,
            componentdict=componentdict,
            ens_idx=ensemble_idx,
            path_base_input=path_base_input,
            keepexe=keepexe,
            **kwargs
        )

    return cloneroot

def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))
