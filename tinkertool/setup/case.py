import datetime, glob, shutil
import os, sys
from netCDF4 import Dataset
from itertools import islice
import subprocess
# Check if the environment variable is set

try: 
    import standard_script_setup
except ImportError:
    print("ERROR: default_simulation_setup.py not found (Part of CIME)")
    raise SystemExit

if os.environ.get('CIMEROOT') is not None:
    import CIME.utils
    CIME.utils.check_minimum_python_version(3, 8)
    CIME.utils.stop_buffering_output()

    import CIME.build as build
    import CIME
    from CIME.case             import Case
    from CIME.utils            import safe_copy
    from CIME.locked_files          import lock_file, unlock_file
else:
    raise ValueError("ERROR: CIMEROOT must be defined in environment")



from tinkertool.setup.namelist import setup_usr_nlstring

def write_user_nl_file(caseroot, usernlfile, user_nl_str):
    """
    write user_nl string to file
    """
    user_nl_file = os.path.join(caseroot,usernlfile)
    print("...Writing to user_nl file: "+usernlfile)
    with open(user_nl_file, "a") as funl:
        funl.write(user_nl_str)
    

def _per_run_case_updates(case: CIME.case, paramdict: dict, ens_idx: str):
    """
    Update and submit the new cloned case, setting namelist parameters according to paramdict

    Parameters
    ----------
    case : CIME.case
        The case object to be updated
    paramdict : dict
        Dictionary of namelist parameters to be updated
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
    case.flush()
    lock_file("env_case.xml",caseroot=caseroot)
    print("...Casename is {}".format(casename))
    print("...Caseroot is {}".format(caseroot))
    print("...Rundir is {}".format(rundir))

    # Add user_nl updates for each run                                                        

    paramLines = []
    print('ensemble_index')
    print(ens_idx.split('.')[-1])

    for var in paramdict.keys():
        paramLines.append("{} = {}\n".format(var,paramdict[var]))    
    usernlfile = os.path.join(caseroot,"user_nl_cam")
    file1 = open(usernlfile, "a")
    file1.writelines(paramLines)
    file1.close()
    print(">> Clone {} case_setup".format(ens_idx))
    case.case_setup()
    print(">> Clone {} create_namelists".format(ens_idx))
    case.create_namelists()
    print(">> Clone {} submit".format(ens_idx))
    subprocess.run(["./case.submit"], cwd=caseroot)

def build_base_case(baseroot: str, 
                    basecasename: str, 
                    overwrite: bool,
                    case_settings: dict,
                    env_run_settings: dict,
                    basecase_startval: str,
                    namelist_collection_dict: dict,
                    cesmroot: str = os.environ.get('CESMROOT')
                    ):
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
        The CESM root directory
    """
    print(">>>>> BUILDING BASE CASE...")
    caseroot = os.path.join(baseroot,basecasename+'.'+basecase_startval)
    if overwrite and os.path.isdir(caseroot):
        shutil.rmtree(caseroot)
    with Case(caseroot, read_only=False) as case:
        if not os.path.isdir(caseroot):
            case.create(os.path.basename(caseroot), cesmroot, case_settings["compset"], 
                        case_settings["res"],
                        machine_name=case_settings["mach"],
                        driver="mct",
                        run_unsupported=True, answer="r",walltime=case_settings["walltime"], 
                        project=case_settings["project"])
            # make sure that changing the casename will not affect these variables                                           
            case.set_value("EXEROOT",case.get_value("EXEROOT", resolved=True))
            case.set_value("RUNDIR",case.get_value("RUNDIR",resolved=True)+basecase_startval)
            case.set_value("RUN_TYPE",env_run_settings["runtype"])
            if env_run_settings.get("ref_case_get") == 'True':
                case.set_value("GET_REFCASE",True)
            if env_run_settings.get("ref_case_name"):
                case.set_value("RUN_REFCASE",env_run_settings["ref_case_name"])
            if env_run_settings.get("ref_case_path"):
                case.set_value("RUN_REFDIR",env_run_settings["ref_case_path"])
                case.set_value("RUN_REFDATE",env_run_settings["run_refdate"])
            case.set_value("STOP_OPTION",env_run_settings["stop_option"])
            case.set_value("STOP_N",env_run_settings["stop_n"])
            case.set_value("RUN_STARTDATE",env_run_settings["run_startdate"])
            if env_run_settings.get("restart_n"):
                case.set_value("REST_OPTION",env_run_settings["stop_option"])
                case.set_value("REST_N",env_run_settings["restart_n"])

            case.set_value("CAM_CONFIG_OPTS", f"{case.get_value('CAM_CONFIG_OPTS',resolved=True)} {env_run_settings['cam_onopts']}")
        print(">> base case_setup...")
        case.case_setup()
        
        print(">> base case write user_nl files...")

        # write user_nl files
        for nl in namelist_collection_dict:
            user_nl_str = setup_usr_nlstring(namelist_collection_dict[nl])
            write_user_nl_file(caseroot, f"user_{nl}", user_nl_str)

        print(">> base case_build...")
        build.case_build(caseroot, case=case)

        return caseroot
    

def clone_base_case(baseroot, basecaseroot, overwrite, paramdict, ensemble_idx):
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
    ensemble_idx : str
    
    """

    print(">>>>> CLONING BASE CASE...")
    cloneroot = os.path.join(baseroot,ensemble_idx)
    
    print(f"member_string= {ensemble_idx}")
    if overwrite and os.path.isdir(cloneroot):
        shutil.rmtree(cloneroot)
    if not os.path.isdir(cloneroot):
        with Case(basecaseroot, read_only=False) as clone:
            clone.create_clone(cloneroot, keepexe=True)
    with Case(cloneroot, read_only=False) as case:
        _per_run_case_updates(case, paramdict, ensemble_idx)

def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))
