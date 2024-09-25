import datetime, glob, shutil
import os, sys
import CIME.build as build
from netCDF4 import Dataset
from itertools import islice
from standard_script_setup import *
from CIME.case             import Case
from CIME.utils            import safe_copy
from argparse              import RawTextHelpFormatter
from CIME.locked_files          import lock_file, unlock_file

def per_run_case_updates(case, ensemble_str, nint, paramdict, ens_idx):
    print(">>>>> BUILDING CLONE CASE...")
    caseroot = case.get_value("CASEROOT")
    basecasename = os.path.basename(caseroot)[:-nint]

    unlock_file("env_case.xml",caseroot=caseroot)
    casename = f"{basecasename}{ensemble_str}"
    case.set_value("CASE",casename)
    rundir = case.get_value("RUNDIR")
    rundir = f"{rundir[:-nint]}{ensemble_str}"
    case.set_value("RUNDIR",rundir)
    case.flush()
    lock_file("env_case.xml",caseroot=caseroot)
    print("...Casename is {}".format(casename))
    print("...Caseroot is {}".format(caseroot))
    print("...Rundir is {}".format(rundir))

    # Add user_nl updates for each run                                                        

    paramLines = []
#    ens_idx = int(ensemble_str)-int(ensemble_startval)
    # ens_idx = int(ensemble_idx)-int(ensemble_startval)
    print('ensemble_index')
    print(ens_idx)
    for var in paramdict.keys():
        paramLines.append("{} = {}\n".format(var,paramdict[var][ens_idx]))

    usernlfile = os.path.join(caseroot,"user_nl_cam")
    print("...Writing to user_nl file: "+usernlfile)
    file1 = open(usernlfile, "a")
    file1.writelines(paramLines)
    file1.close()

    print(">> Clone {} case_setup".format(ensemble_str))
    case.case_setup()
    print(">> Clone {} create_namelists".format(ensemble_str))
    case.create_namelists()
    print(">> Clone {} submit".format(ensemble_str))
    # case.submit()

def build_base_case(baseroot: str, 
                    basecasename: str, 
                    overwrite: bool,
                    case_settings: dict,
                    env_run_settings: dict):
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
            case.set_value("RUNDIR",case.get_value("RUNDIR",resolved=True)+".00")

            case.set_value("RUN_TYPE",env_run_settings["run_type"])
            if env_run_settings.get("ref_case_get"):
                case.set_value("GET_REFCASE",env_run_settings["ref_case_get"])
            if env_run_settings.get("ref_case_name"):
                case.set_value("RUN_REFCASE",env_run_settings["ref_case_name"])
            if env_run_settings.get("ref_case_path"):
                case.set_value("RUN_REFDIR",env_run_settings["ref_case_path"])
                case.set_value("RUN_REFDATE",env_run_settings["ref_case_date"])
            case.set_value("STOP_OPTION",env_run_settings["stop_option"])
            case.set_value("STOP_N",env_run_settings["stop_n"])
            case.set_value("RUN_STARTDATE",env_run_settings["start_date"])
            if env_run_settings.get("restart_n"):
                case.set_value("REST_OPTION",env_run_settings["stop_option"])
                case.set_value("REST_N",env_run_settings["restart_n"])

            case.set_value("CAM_CONFIG_OPTS", 
                           case.get_value("CAM_CONFIG_OPTS",resolved=True)+' '+env_run_settings["cam_conopts"])

        rundir = case.get_value("RUNDIR")
        caseroot = case.get_value("CASEROOT")
        
        print(">> base case_setup...")
        case.case_setup()
        
        print(">> base case write user_nl_cam...")
        usernlfile = os.path.join(caseroot,"user_nl_cam")
        funl = open(usernlfile, "a")
        funl.write(user_nl_string)
        funl.close()
        user_nl_clm_file = os.path.join(caseroot,"user_nl_clm")
        funl = open(user_nl_clm_file, "a")
        funl.write(user_nl_clm_string)
        funl.close()
        
        print(">> base case_build...")
        build.case_build(caseroot, case=case)

        return caseroot
    

def clone_base_case(caseroot, ensemble, overwrite, paramdict, ensemble_num):
    print(">>>>> CLONING BASE CASE...")
    print(ensemble)
    startval = ensemble_startval
    nint = len(ensemble_startval)
    cloneroot = caseroot
    
    for i in range(int(startval), int(startval)+ensemble):
        ensemble_idx = '{{0:0{0:d}d}}'.format(nint).format(i)
        member_string = ensemble_num[i]
        print(f"member_string= {member_string}")
        if ensemble > 1:
            caseroot = f"{cloneroot[:-nint]}{member_string:03d}"
        print(caseroot, member_string, ensemble_idx)
        if overwrite and os.path.isdir(caseroot):
            shutil.rmtree(caseroot)
        if not os.path.isdir(caseroot):
            with Case(cloneroot, read_only=False) as clone:
                clone.create_clone(caseroot, keepexe=True)
        with Case(caseroot, read_only=False) as case:
            per_run_case_updates(case, member_string, nint, paramdict, ensemble_idx)

def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))
