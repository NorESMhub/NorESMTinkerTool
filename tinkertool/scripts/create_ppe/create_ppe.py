import os
import logging
import subprocess
from pathlib import Path

from tinkertool.utils.custom_logging import log_info_detailed, setup_logging
from tinkertool.setup.case import build_base_case, clone_base_case
from tinkertool.scripts.create_ppe.config import (
    CreatePPEConfig,
    BuildPPEConfig,
    CheckedBuildPPEConfig,
    SubmitPPEConfig,
    CheckedSubmitPPEConfig
)
from tinkertool.setup.setup_cime_connection import add_CIME_paths

try:
    env_cesmroot = os.environ.get('CESMROOT')
    if env_cesmroot is None:
        raise ImportError("CESMROOT environment variable not set")
    env_cesmroot = Path(env_cesmroot)
    add_CIME_paths(cesmroot=env_cesmroot)
except ImportError:
    print("ERROR: add_CIME_paths failed, update CESMROOT environment variable")
    raise SystemExit
try:
    from CIME.case import Case
except ImportError:
    print("ERROR: CIME.case not found, or unable to find Case class")
    raise SystemExit

unsuccessful_build_msg = """> Build was not successful for all cases. Please check the logs. \n
    > Exiting PPE creation process.
    > If you want to submit the cases after a successful build script using python:
    >> from pathlib import Path
    >> from tinkertool.scripts.create_ppe.create_ppe import check_build, prestage_ensemble, submit_ppe
    >> from tinkertool.scripts.create_ppe.config import SubmitPPEConfig, PrestageEnsembleConfig
    >> ensemble_members = [Path(case).resolve() for case in Path('<baseroot>')iterdir() if case.is_dir() and 'ensemble_member' in case.name]
    >> submit_config = SubmitPPEConfig(cases=ensemble_members, verbose=<verbose_lvl>, log_file=<log_file>, log_mode=<log_mode>)
    >> if not check_build(submit_config):
    >>     raise RuntimeError("Build was not successful for all cases. Please check the logs.")
    >> if not prestage_ensemble(submit_config):
    >>     raise RuntimeError("Prestage was not successful for all cases. Please check the logs.")
    >> submit_ppe(submit_config)

    > or equivalently in bash using the CLI:

    >> ensemble_members=( $(find <baseroot> -type d -name '*ensemble_member*' -exec realpath {} \;)
    >> check-build "${ensemble_members[@]}"  -vv -l <log_file> -lm <log_mode>
    >> prestage-ensemble "${ensemble_members[@]}" -vv -l <log_file> -lm <log_mode>
    >> submit-ppe "${ensemble_members[@]}" -vv -l <log_file> -lm <log_mode>
    >> for details on the commands, run 'check-build --help', 'prestage-ensemble --help' and 'submit-ppe --help'
"""

def create_ppe(config: CreatePPEConfig):

    logging.info("> Starting PPE creation")

    # create a BuildPPEConfig object from config
    build_config = BuildPPEConfig(
        simulation_setup_path=config.simulation_setup_path,
        build_base_only=config.build_base_only,
        keepexe=config.keepexe,
        overwrite=config.overwrite,
        verbose=config.verbose,
        log_dir=config.log_dir,
        log_mode=config.log_mode
    )

    # then build the ppe cases
    base_case, cases = build_ppe(build_config)
    if cases is None:
        if not build_config.build_base_only:
            err_msg = f"build_ppe returned 'None' but list of cases was expected since build_base_only={build_config.build_base_only}"
            logging.error(err_msg)
            raise RuntimeError(err_msg)
        else:
            # build_base_only=True, so no cases to submit
            logging.info(">> Base case built successfully. No ensemble cases to submit.")
            return

    cases_for_check_build = [base_case]
    if cases is None:
        if config.build_only:
            err_msg = "build_ppe returned 'None' but list of cases was" \
            f"expected since build_only={config.build_only}"
            logging.error(err_msg)
            raise RuntimeError(err_msg)

    cases_for_check_build.extend(cases)

    check_build_config = SubmitPPEConfig(
        cases=cases_for_check_build,
        verbose=config.verbose,
        log_dir=config.log_dir,
        log_mode=config.log_mode
    )
    # check if build was successful
    check_build_success = check_build(check_build_config)

    if not check_build_success:
        logging.error(unsuccessful_build_msg)
        return

    if not config.build_only:
        prestage_and_submit_ensemble_config = SubmitPPEConfig(
            cases=cases,
            verbose=config.verbose,
            log_dir=config.log_dir,
            log_mode=config.log_mode
        )
        prestage_ensemble(prestage_and_submit_ensemble_config)
        # create SubmitPPEConfig object from config and cases
        submit_ppe(prestage_and_submit_ensemble_config)

    logging.info("> Finished PPE creation")

def build_ppe(config: BuildPPEConfig) -> tuple[Path, list[Path] | None]:

    # check if BuildPPEConfig is valid
    # returned config is a CheckedBuildPPEConfig object which has additional data variables
    # compare to the dataclass BuildPPEConfig.
    checked_config: CheckedBuildPPEConfig = config.get_checked_and_derived_config()

    # set up logging if not already set
    if not logging.getLogger('tinkertool_log').handlers:
        setup_logging(checked_config.verbose, checked_config.log_file, checked_config.log_mode, 'tinkertool_log')
        log_info_detailed('tinkertool_log', 'tinkertool_log logger set up')

    logging.info(">> Starting PPE case building")
    log_info_detailed('tinkertool_log', f"Building with config: {config.describe(return_string=True)}") # type: ignore

    if not checked_config.clone_only_during_build:
        basecaseroot = build_base_case(
            basecaseroot=checked_config.baseroot.joinpath(checked_config.basecasename),
            overwrite=checked_config.overwrite,
            case_settings=dict(checked_config.simulation_setup['create_case']),
            env_pe_settings=dict(checked_config.simulation_setup['env_pe']) if 'env_pe' in checked_config.simulation_setup.sections() else {},
            env_run_settings=dict(checked_config.simulation_setup['env_run']),
            env_build_settings=dict(checked_config.simulation_setup['env_build']) if 'env_build' in checked_config.simulation_setup.sections() else {},
            namelist_collection_dict=checked_config.namelist_collection_dict,
        )
        logging.info(f">> Base case created successfully at {basecaseroot}")
    else:
        basecaseroot = checked_config.baseroot.joinpath(checked_config.basecasename)

    if checked_config.build_base_only:
        logging.info(">> No ensembles created as build_base_only is set to True.")
        return basecaseroot, None
    else:
        cases = []
        for i, idx in zip(checked_config.ensemble_num, range(len(checked_config.ensemble_num))):
            log_info_detailed('tinkertool_log', f"Building ensemble {i} of {checked_config.num_sims}")
            ensemble_idx = f"{i:03d}"
            temp_param_dict = {k : v[idx] for k,v in checked_config.paramdict.items()}
            # Special treatment for chem_mech.in changes:
            if 'chem_mech_in' in temp_param_dict:
                # remove all chem_mech_in keys that are not chem_mech_in (there can anyway only be one chem_mech.in file)
                keys_in_dic = list(temp_param_dict.keys())
                for v in keys_in_dic:
                    if v[-12:]=='chem_mech_in' and len(v)>12:
                        log_info_detailed('tinkertool_log', f'Deleting {v} from parameter directory')
                        del temp_param_dict[v]
            # special treatment for non-mandatory parameters to clone_base_case
            clone_base_case_kwargs = {}
            if checked_config.simulation_setup.has_section('lifeCycleValues'):
                clone_base_case_kwargs['lifeCycleMedianRadius'] = checked_config.simulation_setup['lifeCycleValues'].get('medianradius', None)
                clone_base_case_kwargs['lifeCycleSigma'] = checked_config.simulation_setup['lifeCycleValues'].get('sigma', None)
            clonecaseroot = clone_base_case(
                baseroot=checked_config.baseroot,
                basecaseroot=basecaseroot,
                overwrite=checked_config.overwrite,
                paramdict=temp_param_dict,
                componentdict=checked_config.componentdict,
                ensemble_idx=ensemble_idx,
                path_base_input=checked_config.paramfile_path.parent,
                keepexe=checked_config.keepexe,
                **clone_base_case_kwargs
            )
            cases.append(clonecaseroot)
            logging.info(f">> Ensemble {i} of {checked_config.ensemble_num[-1]} created successfully.")

    return basecaseroot, cases

def check_build(config: SubmitPPEConfig) -> bool:
    """Check if the build was successful by checking for case.build success in each case directories CaseStatus

    Parameters
    ----------
    config : SubmitPPEConfig
        Configuration object containing the cases to check and logging settings.
    Returns
    -------
    bool
        True if all cases have a successful build, False otherwise.
    """

    # check if SumitPPEConfig is valid
    checked_config: CheckedSubmitPPEConfig = config.get_checked_and_derived_config()

    # set up logging if not already set
    if not logging.getLogger('tinkertool_log').handlers:
        setup_logging(checked_config.verbose, checked_config.log_file, checked_config.log_mode, 'tinkertool_log')
        log_info_detailed('tinkertool_log', 'tinkertool_log logger set up')


    all_build_success = True
    for case in checked_config.cases:
        case_status_file = os.path.join(case, 'CaseStatus')
        if not os.path.exists(case_status_file):
            logging.error(f"CaseStatus file not found in {case}.")
            all_build_success = False
            continue

        with open(case_status_file, 'r') as file:
            found = False
            for line in file:
                if 'case.build success' in line:
                    found = True
                    break

        if found:
            log_info_detailed("tinkertool_log", f"Build successful for case {case}.")
        else:
            logging.error(f"Build failed for case {case}. cat {case.joinpath('CaseStatus')} for details.")
            all_build_success = False

    return all_build_success

def prestage_ensemble(config: SubmitPPEConfig) -> bool:
    """Prestage the ensemble members by copying the base case input files to each member's input directory.

    Parameters
    ----------
    config : PrestageEnsembleConfig
        Configuration object containing the cases to prestage and logging settings.
    """

    # check if PrestageEnsembleConfig is valid
    checked_config: CheckedSubmitPPEConfig = config.get_checked_and_derived_config()

    # set up logging if not already set
    if not logging.getLogger('tinkertool_log').handlers:
        setup_logging(checked_config.verbose, checked_config.log_file, checked_config.log_mode, 'tinkertool_log')
        log_info_detailed('tinkertool_log', 'tinkertool_log logger set up')

    logging.info(">> Starting PPE prestaging")

    all_prestage_success = True
    for caseroot in checked_config.cases:
        with Case(caseroot, read_only=False) as case:

            rundir = Path(case.get_value('RUNDIR')).resolve()
            run_type = case.get_value('RUN_TYPE')
            run_refdir = Path(case.get_value('RUN_REFDIR')).resolve()
            if case.get_value('GET_REFCASE') == 'TRUE':
                logging.warning(
                    f"Case {case} has \n"\
                    "> 'GET_REFCASE'='TRUE' with \n"\
                    f"> 'RUN_REFDIR'={run_refdir} \n"\
                    "skipping manual prestaging."\
                    "Note that this might cause a crash if cases are submitted simultaneously."
                )
            else:
                # copy the netcdf files from the 'RUN_REFDIR' to the 'RUNDIR'
                # and set 'RUN_REFDIR'='RUNDIR'. This is needed to ensure that the
                # cases can run independently and do not interfere with each other.
                ref_netcdf_files = [str(file) for file in run_refdir.glob('*.nc')]
                if ref_netcdf_files:
                    try:
                        subprocess.run(
                            [
                                'rsync', '--archive',
                                *ref_netcdf_files,
                                rundir
                            ],
                            cwd=caseroot,
                            executable='/bin/bash',
                            check=True,
                            shell=True
                        )
                    except subprocess.CalledProcessError as e:
                        error_msg = f"Failed to prestage ref_netcdf_files files for case {caseroot}."
                        logging.error(error_msg)
                    case.set_value('RUN_REFDIR', rundir)
                else:
                    logging.warning(f"No netcdf files found in {run_refdir}. Skipping prestaging for case {caseroot}.")
                    all_prestage_success = False

                if run_type == 'branch':
                    # in a branch run, we need to prestage the rpointer files as well
                    # copy the rpointer files from the original run_refdir to the rundir
                    # and set 'DRV_RESTART_POINTER' to the rpointer file name with the correct date and time
                    rpointer_files = [str(file) for file in run_refdir.glob('rpointer*')]
                    if rpointer_files:
                        try:
                            subprocess.run(
                                [
                                    'rsync', '--archive',
                                    *rpointer_files,
                                    rundir
                                ],
                                cwd=caseroot,
                                executable='/bin/bash',
                                check=True,
                                shell=True
                            )
                        except subprocess.CalledProcessError as e:
                            error_msg = f"Failed to prestage rpointer files for case {caseroot}."
                            logging.error(error_msg)

                        case.set_value('DRV_RESTART_POINTER', f"rpointer.cpl.{case.get_value('RUN_REFDATE')}-{case.get_value('RUN_REFTOD')}")
                    else:
                        logging.warning(f"No rpointer files found in {run_refdir}. Skipping prestaging for case {caseroot}.")
                        all_prestage_success = False

    logging.info(f">> {len(checked_config.cases)} cases prestaged successfully.")
    return all_prestage_success

def submit_ppe(config: SubmitPPEConfig):

    # check if SumitPPEConfig is valid
    checked_config: CheckedSubmitPPEConfig = config.get_checked_and_derived_config()

    # set up logging if not already set
    if not logging.getLogger('tinkertool_log').handlers:
        setup_logging(checked_config.verbose, checked_config.log_file, checked_config.log_mode, 'tinkertool_log')
        log_info_detailed('tinkertool_log', 'tinkertool_log logger set up')

    logging.info(">> Starting SCAM PPE case submission")

    # iterate over the cases and submit them
    for case in checked_config.cases:
        os.chdir(case)
        log_info_detailed('tinkertool_log', f"Submitting case {case.name}")
        logging.debug(f"Current working directory: {os.getcwd()}")
        subprocess.run(
            ['./case.submit'],
            check=True,
            cwd=case
        )
        log_info_detailed('tinkertool_log', f"Clone {case.name} submitted successfully.")

    logging.info(f">> {len(checked_config.cases)} cases submitted successfully.")
    logging.info(">> Check the queue with 'squeue -u <USER>' command")
    logging.info(">> Check the log files in each case directory for more information")
    logging.info(">> Finished PPE case submission")
