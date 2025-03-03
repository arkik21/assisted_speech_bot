from helpers.clob_client import create_clob_client


def get_market(condition_id: str):
    return create_clob_client().get_market(condition_id=condition_id)
