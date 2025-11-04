# ------------------------ #
# --- Import libraries --- #
# ------------------------ #
import os
import shutil
import logging
import subprocess
from pathlib import Path
from itertools import islice

from tinkertool.setup.namelist import setup_usr_nlstring, write_user_nl_file
from tinkertool.setup.setup_cime_connection import add_CIME_paths

try:
    environ_CESMROOT = os.environ.get('CESMROOT')
    if environ_CESMROOT is None:
        raise ImportError("CESMROOT environment variable not set")
    add_CIME_paths(cesmroot=environ_CESMROOT)
except ImportError:
    print("ERROR: add_CIME_paths failed, update CESMROOT environment variable")
    raise SystemExit

try:
    import CIME
except ImportError:
    print("ERROR: CIME not found, update CESMROOT environment variable")
    raise SystemExit
try:
    from CIME.Tools.standard_script_setup import check_minimum_python_version
    check_minimum_python_version(3, 8)
except ImportError:
    print('ERROR: CIME.Tools.standard_script_setup not found, or unable to use check_minimum_python_version()')
try:
    os.environ["PYTHONUNBUFFERED"] = "1"
except ImportError:
    print("ERROR: os.environ not found, unable to set PYTHONUNBUFFERED")
    raise SystemExit
try:
    import CIME.build as build
except ImportError:
    print("ERROR: CIME.build not found, or unable to find build module")
    raise SystemExit
try:
    from CIME.case import Case
except ImportError:
    print("ERROR: CIME.case not found, or unable to find Case class")
    raise SystemExit
try:
    from CIME.locked_files import lock_file, unlock_file
except ImportError:
    print("ERROR: CIME.locked_files not found, or unable to find lock_file() and unlock_file()")
    raise SystemExit

# get the logger - assuming this is run from create_ppe.build_ppe so that tinkertool_log is set up
logger = logging.getLogger('tinkertool_log')
logger.debug("CIME imported successfully")

# ------------------------ #
# --- Helper functions --- #
# ------------------------ #

def iterate_dict_to_set_value(
    case:           CIME.case,
    settings_dict:  dict,
    dict_name:      str
):
    """
    Iterate through a dictionary and set the values in the case object

    Parameters
    ----------
    case : CIME.case
        The case object to be updated
    settings_dict : dict
        Dictionary of settings to be applied to the case
    """
    for key, value in settings_dict.items():
        try:
            case.set_value(key, value)
        except Exception as error:
            logger.warning(f"WARNING: {key} from {dict_name} not set in case: {error}")
            continue

def _per_run_case_updates(
    case: CIME.case,
    paramdict: dict,
    componentdict: dict,
    ens_idx: str,
    path_base_input:str ='',
    keepexe: bool=False,
    lifeCycleMedianRadius=None,
    lifeCycleSigma=None
):
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

    logger.info(">> Building clone case {}...".format(ens_idx))

    caseroot = case.get_value("CASEROOT")
    casename = os.path.basename(caseroot)
    unlock_file("env_case.xml",caseroot=caseroot)
    case.set_value("CASE", casename)
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

    logger.info("...Casename is {}".format(casename))
    logger.info("...Caseroot is {}".format(caseroot))
    logger.info("...Rundir is {}".format(rundir))

    # --- Add user_nl updates for each run
    # find all comonents that we are editing
    components = list(set(componentdict.values()))

    paramLinesDict = {component: [] for component in components}

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
        unlock_file("env_build.xml", caseroot=caseroot)
        value = case.get_value("CAM_CONFIG_OPTS", resolved=False)
        case.set_value("CAM_CONFIG_OPTS", f"{value} --usr_mech_infile {caseroot}/{chem_mech_file.name}")
        case.flush()
        lock_file("env_build.xml", caseroot=caseroot)


    logger.info(">> Clone {} case_setup".format(ens_idx))
    case.case_setup()
    logger.info(">> Clone {} create_namelists".format(ens_idx))
    case.create_namelists()
    if keepexe == False:
        logger.info(">> Clone {} build".format(ens_idx))
        build.case_build(caseroot, case=case)

def build_base_case(
    baseroot:                   str,
    basecasename:               str,
    overwrite:                  bool,
    case_settings:              dict,
    env_pe_settings:            dict,
    env_run_settings:           dict,
    env_build_settings:         dict,
    namelist_collection_dict:   dict
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
    env_pe_settings : dict
        Dictionary of environment parallel execution settings
    env_run_settings : dict
        Dictionary of environment run settings
    namelist_collection_dict : dict
        Dictionary of namelist collections for the different components
    verbose : int
        Verbosity level for logging

    Returns
    -------
    str
        The root directory of the base case
    """
    logger.info(">>> BUILDING BASE CASE...")
    caseroot = os.path.join(baseroot, basecasename)
    if overwrite and os.path.isdir(caseroot):
        shutil.rmtree(caseroot)
    with Case(caseroot, read_only=False) as case:
        if not os.path.isdir(caseroot):
            logger.info('Creating base case directory: {}'.format(caseroot))
            # create the case using the case_settings
            case.create(
                casename=os.path.basename(caseroot),
                srcroot=case_settings.pop("cesmroot"),
                compset_name=case_settings.pop("compset"),
                grid_name=case_settings.pop("res"),
                machine_name=case_settings.pop("mach"),
                project=case_settings.pop("project"),
                driver="nuopc",
                run_unsupported=True,
                answer="r",
                **case_settings
            )
            case.record_cmd(init=True)
        else:
            if not case.read_only:
                logger.info('Reusing existing case directory: {}'.format(caseroot))
            else:
                logger.warning('Base case directory exists but is read-only: {}'.format(caseroot))


        # set the case environment variables
        # first using the case's own values
        case.set_value("EXEROOT", case.get_value("EXEROOT", resolved=True))
        case.set_value("RUNDIR", case.get_value("RUNDIR", resolved=True))
        # set the PE settings
        # check if the env_pe_settings are not empty dict, or all entries are None
        if not env_pe_settings or all(value is None for value in env_pe_settings.values()):
            logging.warning("No environment parallel execution settings provided, using default values.")
        else:
            logger.info(">>> Setting environment parallel execution settings...")
            iterate_dict_to_set_value(
                case=case,
                settings_dict=env_pe_settings,
                dict_name='env_pe_settings'
            )

        logger.info(">>> base case_setup...")
        case.case_setup()

        logger.info(">>> Setting environment run settings...")
        # set the run settings
        case.set_value("RUN_TYPE", env_run_settings.pop("RUN_TYPE"))
        case.set_value('JOB_WALLCLOCK_TIME', env_run_settings.pop('JOB_WALLCLOCK_TIME_RUN'), subgroup='case.run')
        case.set_value('JOB_WALLCLOCK_TIME', env_run_settings.pop('JOB_WALLCLOCK_TIME_ARCHIVE'), subgroup='case.st_archive')
        case.set_value('JOB_WALLCLOCK_TIME', env_run_settings.pop('JOB_WALLCLOCK_TIME_COMPRESS'), subgroup='case.compress')
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

        if env_run_settings.get('CAM_CONFIG_OPTS') is not None:
            if env_run_settings.get('cam_onopts'):
                logging.warning(
                    "Both 'CAM_CONFIG_OPTS' and 'cam_onopts' were provided. "
                    "'CAM_CONFIG_OPTS' will overwrite all previous options including 'cam_onopts'."
                )
            case.set_value('CAM_CONFIG_OPTS', env_run_settings.pop('CAM_CONFIG_OPTS'))
        elif env_run_settings.get('cam_onopts') is not None:
            current_opts = case.get_value('CAM_CONFIG_OPTS', resolved=True)
            new_opts = f"{current_opts} {env_run_settings.pop('cam_onopts')}".strip()
            case.set_value('CAM_CONFIG_OPTS', new_opts)

        # check if there are any additional run settings
        if env_run_settings or any(value is not None for value in env_run_settings.values()):
            iterate_dict_to_set_value(
                case=case,
                settings_dict=env_run_settings,
                dict_name='env_run_settings'
            )

        case.set_value("DEBUG", env_build_settings.pop("DEBUG", "FALSE"))
        # check if the env_build_settings are not empty dict, or all entries are None
        if not env_build_settings or all(value is None for value in env_build_settings.values()):
            logging.warning("No environment build settings provided, using default values.")
        else:
            logger.info(">>> Setting environment build settings...")
            iterate_dict_to_set_value(
                case=case,
                settings_dict=env_build_settings,
                dict_name='env_build_settings'
            )

        logger.info(">>> base case write user_nl files...")
        # write user_nl files
        for nl_control_filename in namelist_collection_dict.keys():
            # get the component name from the file name assuming control_<component>.ini
            component_name = nl_control_filename.split('_')[1].split('.')[0]
            user_nl_str = setup_usr_nlstring(namelist_collection_dict[nl_control_filename], component_name=component_name)
            write_user_nl_file(caseroot, f"user_nl_{component_name}", user_nl_str)

        logger.info(">> base case_build...")
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

    logger.info(">>> CLONING BASE CASE for member {}...".format(ensemble_idx))
    cloneroot = os.path.join(baseroot, f'ensemble_member.{ensemble_idx}')

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
