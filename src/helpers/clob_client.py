import os
from dotenv import load_dotenv

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
from py_clob_client.constants import POLYGON


def create_clob_client() -> ClobClient:
    load_dotenv()

    chain_id = POLYGON
    host = os.getenv('HOST')
    key = os.getenv('PK')

    if os.getenv('CLOB_API_KEY'):
        creds = ApiCreds(
            api_key=os.getenv('CLOB_API_KEY'),
            api_secret=os.getenv('CLOB_SECRET'),
            api_passphrase=os.getenv('CLOB_PASS_PHRASE'),
        )
    else:
        creds = None

    return ClobClient(host=host, key=key, chain_id=chain_id, creds=creds)

