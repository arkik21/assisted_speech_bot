import os
from dotenv import load_dotenv

from py_clob_client.order_builder.constants import BUY

from helpers.generate_wallet import generate_new_wallet
from helpers.set_allowances import set_allowances
from api_keys.get_api_credentials import get_api_creds, generate_api_keys
from markets.get_markets import get_market
from trades.trade_specific_market import create_and_submit_order

load_dotenv()

# Step 1: Generate a new wallet and save the PBK with PK to .env
if os.getenv('PK') is None:
    generate_new_wallet()

# Step 2: Send some MATIC to the generated wallet to update allowances
set_allowances()

# Step 3: Generate API credentials so that we can communicate with Polymarket
if os.getenv('CLOB_API_KEY') is None:
    generate_api_keys()
else:
    get_api_creds()

# Step 4: Find the condition ID for the market you want to trade and retrieve market info from CLOB
market = get_market('0xbb96f092cb5d54138c6af2ae824bb276c3e20969fb2acfced30ac7f88f60862e')
yes_token = next((item for item in market['tokens'] if item.get('outcome') == 'Yes'), None)

# Step 5: Fill order data and choose the side you want to buy
create_and_submit_order(yes_token['token_id'], BUY, 0.06, 30)