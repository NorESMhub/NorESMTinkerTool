import os
import logging

from tinkertool.utils.logging import setup_logging
from tinkertool.utils.run_subprocess import run_command
from tinkertool.setup.case import build_base_case, clone_base_case
from tinkertool.scripts.create_ppe.config import (
    CreatePPEConfig,
    BuildPPEConfig,
    CheckedBuildPPEConfig,
    SubmitPPEConfig,
    CheckedSubmitPPEConfig
)

def create_ppe(config: CreatePPEConfig):

    # set up logging if not already set
    # tinkertool log
    logger = logging.getLogger('tinkertool_log')
    if not logger.handlers:
        setup_logging(config.verbose, config.log_file, config.log_mode, 'tinkertool_log')
        logger.info_detailed('tinkertool_log logger set up')

    logger.info("> Starting SCAM PPE creation")

    # create a BuildPPEConfig object from config
    build_config = BuildPPEConfig(
        simulation_setup_path=config.simulation_setup_path,
        build_base_only=config.build_base_only,
        keepexe=config.keepexe,
        overwrite=config.overwrite,
        verbose=config.verbose,
        log_file=config.log_file,
        log_mode=config.log_mode
    )
    # then build the ppe cases
    cases = build_ppe(build_config)

    if not config.build_only:
        # create SubmitPPEConfig object from config and cases
        submit_config = SubmitPPEConfig(
            cases=cases,
            verbose=config.verbose,
            log_file=config.log_file,
            log_mode=config.log_mode
        )
        submit_ppe(submit_config)

    logger.info("> Finished SCAM PPE creation")

def build_ppe(config: BuildPPEConfig):

    # check if BuildPPEConfig is valid
    # returned config is a CheckedBuildPPEConfig object which has additional data variables
    # compare to the dataclass BuildPPEConfig.
    config: CheckedBuildPPEConfig = config.get_checked_and_derived_config()

    # set up logging if not already set
    logger = logging.getLogger('tinkertool_log')
    if not logger.handlers:
        setup_logging(config.verbose, config.log_file, config.log_mode, 'tinkertool_log')
        logger.info_detailed('tinkertool_log logger set up')

    logger.info(">> Starting SCAM PPE case building")
    logger.info_detailed(f"Building with config: {config.describe(return_string=True)}")

    cases = []

    if not config.clone_only_during_build:
        basecaseroot = build_base_case(
            baseroot=config.baseroot,
            basecasename=config.basecasename,
            overwrite=config.overwrite,
            case_settings=config.simulation_setup['create_case'],
            env_pe_settings=config.simulation_setup['env_pe'] if 'env_pe' in config.simulation_setup.sections() else {},
            env_run_settings=config.simulation_setup['env_run'],
            env_build_settings=config.simulation_setup['env_build'] if 'env_build' in config.simulation_setup.sections() else {},
            namelist_collection_dict=config.namelist_collection_dict,
        )
        logger.info(f">> Base case created successfully at {basecaseroot}")
    else:
        basecaseroot = os.path.join(
            config.baseroot,
            config.basecasename
        )

    if config.build_base_only:
        logger.info(">> No ensembles created as build_base_only is set to True.")
        return None
    else:
        for i, idx in zip(config.ensemble_num, range(len(config.ensemble_num))):
            logger.info_detailed(f"Building ensemble {i} of {config.num_sims}")
            ensemble_idx = f"{i:03d}"
            temp_param_dict = {k : v[idx] for k,v in config.paramdict.items()}
            # Special treatment for chem_mech.in changes:
            if 'chem_mech_in' in temp_param_dict:
                # remove all chem_mech_in keys that are not chem_mech_in (there can anyway only be one chem_mech.in file)
                keys_in_dic = list(temp_param_dict.keys())
                for v in keys_in_dic:
                    if v[-12:]=='chem_mech_in' and len(v)>12:
                        logger.info_detailed(f'Deleting {v} from parameter directory')
                        del temp_param_dict[v]
            # special treatment for non-mandatory parameters to clone_base_case
            clone_base_case_kwargs = {}
            if config.simulation_setup.has_section('lifeCycleValues'):
                clone_base_case_kwargs['lifeCycleMedianRadius'] = config.simulation_setup['lifeCycleValues'].get('medianradius', None)
                clone_base_case_kwargs['lifeCycleSigma'] = config.simulation_setup['lifeCycleValues'].get('sigma', None)
            clonecaseroot = clone_base_case(
                baseroot=config.baseroot,
                basecaseroot=basecaseroot,
                overwrite=config.overwrite,
                paramdict=temp_param_dict,
                componentdict=config.componentdict,
                ensemble_idx=ensemble_idx,
                path_base_input=config.paramfile_path.parent,
                keepexe=config.keepexe,
                **clone_base_case_kwargs
            )
            cases.append(clonecaseroot)
            logger.info(f">> Ensemble {i} of {config.num_sims} created successfully.")

    return cases

def submit_ppe(config: SubmitPPEConfig):

    # check if SumitPPEConfig is valid
    config: CheckedSubmitPPEConfig = config.get_checked_and_derived_config()

    # set up logging if not already set
    logger = logging.getLogger('tinkertool_log')
    if not logger.handlers:
        setup_logging(config.verbose, config.log_file, config.log_mode, 'tinkertool_log')
        logger.info_detailed('tinkertool_log logger set up')

    logger.info(">> Starting SCAM PPE case submission")

    # iterate over the cases and submit them
    for case in config.cases:
        os.chdir(case)
        logger.info_detailed(f"Submitting case {case.name}")
        logger.debug(f"Current working directory: {os.getcwd()}")
        subprocess.run(
            ['./case.submit'],
            check=True,
            cwd=case
        )
        logger.info_detailed(f"Clone {case.name} submitted successfully.")

    logger.info(f">> {len(config.cases)} cases submitted successfully.")
    logger.info(">> Check the queue with 'squeue -u <USER>' command")
    logger.info(">> Check the log files in each case directory for more information")
    logger.info(">> Finished SCAM PPE case submission")
