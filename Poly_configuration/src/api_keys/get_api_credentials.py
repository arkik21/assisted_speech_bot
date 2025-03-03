from dotenv import set_key, load_dotenv
from helpers.clob_client import create_clob_client
import os

def generate_api_keys():
    client = create_clob_client()
        
    api_credentials = client.create_api_key()

    env_path = '.env'  # Path to your .env file
    load_dotenv(env_path)  # Load existing .env file if present

    set_key(env_path, 'CLOB_API_KEY', api_credentials.api_key)
    set_key(env_path, 'CLOB_SECRET', api_credentials.api_secret)
    set_key(env_path, 'CLOB_PASS_PHRASE', api_credentials.api_passphrase)

def get_api_creds():
    # Load API credentials from .env file
    load_dotenv()  # Load environment variables from .env
    
    return {
        "apiKey": os.getenv('CLOB_API_KEY'),
        "secret": os.getenv('CLOB_SECRET'),
        "passphrase": os.getenv('CLOB_PASS_PHRASE')
    }

