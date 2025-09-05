import logging

from tinkertool.scripts.create_ppe.config import (
    BuildPPEConfig,
    CheckedBuildPPEConfig,
    CheckedSubmitPPEConfig,
    CreatePPEConfig,
    SubmitPPEConfig,
)
from tinkertool.setup.case import build_base_case, clone_base_case
from tinkertool.utils.logging import setup_logging
from tinkertool.utils.run_subprocess import run_command


def create_ppe(config: CreatePPEConfig):

    # Set up logging
    setup_logging(config.verbose, config.log_file, config.log_mode)
    logging.info("> Starting SCAM PPE creation")

    # create a BuildPPEConfig object from config
    build_config = BuildPPEConfig(
        simulation_setup_path=config.simulation_setup_path,
        build_base_only=config.build_base_only,
        keepexe=config.keepexe,
        overwrite=config.overwrite,
        verbose=config.verbose,
        log_file=config.log_file,
        log_mode=config.log_mode,
    )
    # then build the ppe cases
    cases = build_ppe(build_config)

    if not config.build_only:
        # create SubmitPPEConfig object from config and cases
        submit_config = SubmitPPEConfig(
            cases=cases,
            verbose=config.verbose,
            log_file=config.log_file,
            log_mode=config.log_mode,
        )
        submit_ppe(submit_config)


def build_ppe(config: BuildPPEConfig):

    # check if BuildPPEConfig is valid
    # returned config is a CheckedBuildPPEConfig object which has additional data variables
    # compare to the dataclass BuildPPEConfig.
    config: CheckedBuildPPEConfig = config.check_and_handle_arguments()
    logging.info(">> Starting SCAM PPE case building")
    logging.info_detailed(
        f">> Building with config: {config.describe(return_string=True)}"
    )

    cases = []
    basecaseroot = build_base_case(
        baseroot=config.baseroot,
        basecasename=config.basecasename,
        overwrite=config.overwrite,
        case_settings=config.simulation_setup["create_case"],
        env_run_settings=config.simulation_setup["env_run"],
        env_build_settings=config.simulation_setup["env_build"],
        basecase_startval=config.basecase_id,
        namelist_collection_dict=config.namelist_collection_dict,
        cesmroot=config.cesm_root,
    )
    cases.append(basecaseroot)

    if config.build_base_only:
        logging.info(f">> Base case {config.basecasename} created successfully.")
    else:
        start_num = 1
        for i, idx in zip(
            range(start_num, config.num_sims + start_num), config.ensemble_num
        ):
            logging.info_detailed(f">> Building ensemble {i} of {config.num_sims}")
            ensemble_idx = f"{config.basecasename}.{i:03d}"
            temp_dict = {k: v[idx] for k, v in config.paramdict.items()}
            # Special treatment for chem_mech.in changes:
            if "chem_mech_in" in temp_dict:
                # remove all chem_mech_in keys that are not chem_mech_in (there can anyway only be one chem_mech.in file)
                keys_in_dic = list(temp_dict.keys())
                for v in keys_in_dic:
                    if v[-12:] == "chem_mech_in" and len(v) > 12:
                        print(f"Deleting {v} from parameter directory")
                        del temp_dict[v]
            clonecaseroot = clone_base_case(
                baseroot=config.baseroot,
                basecaseroot=basecaseroot,
                overwrite=config.overwrite,
                paramdict=temp_dict,
                ensemble_idx=ensemble_idx,
                path_base_input=config.paramfile_path.parent,
                keepexe=config.keepexe,
                lifeCycleMedianRadius=config["lifeCycleValues"].get(
                    "medianradius", None
                ),
                lifeCycleSigma=config["lifeCycleValues"].get("sigma", None),
            )
            cases.append(clonecaseroot)
            logging.info(f">> Ensemble {i} of {config.num_sims} created successfully.")

    return cases


def submit_ppe(config: SubmitPPEConfig):

    # check if SumitPPEConfig is valid
    config: CheckedSubmitPPEConfig = config.check_and_handle_arguments()

    # set up logging if not already set
    if not logging.getLogger().hasHandlers():
        setup_logging(config.verbose, config.log_file, config.log_mode)
    logging.info(">> Starting SCAM PPE case submission")

    # iterate over the cases and submit them
    for case in config.cases:

        run_command(
            f"./case.submit", error_msg=f"Failed to submit case {case}", cwd=case
        )
        logging.info_detailed(f"Clone {case.name} submitted successfully.")

    logging.info(f">> {len(config.cases)} cases submitted successfully.")
    logging.info(">> Check the queue with 'squeue -u <USER>' command")
    logging.info(">> Check the log files in each case directory for more information")
    logging.info(">> Finished SCAM PPE case submission")
