def set_value_with_status_update(case, key, value, subgroup=None, kill_on_error=False) -> bool:
    try:
        case.set_value(key, value, subgroup)
    except Exception as error:
        logger.warning(f"WARNING: New value {value} where not successfully set for {key} in case: {error}")
        if kill_on_error:
            exit()
        else:
            return False
    append_case_status(
        phase='case.set_value',
        status='success',
        msg=f'{key} set to {value}',
        caseroot=case.get_value("CASEROOT"),
        gitinterface=case._gitinterface
    )
    return True