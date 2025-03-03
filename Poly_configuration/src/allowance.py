import asyncio
from helpers.clob_client import create_clob_client  # Add this import
from py_clob_client.client import ClobClient

async def check_and_fix_allowance(client, amount):
    EXCHANGE_ADDRESS = "" # Polymarket exchange address here
    USDC_ADDRESS = "" # Add your address here
    
    allowance = await client.get_allowance(USDC_ADDRESS, EXCHANGE_ADDRESS)
    
    if allowance < amount:
        await client.approve_usdc(EXCHANGE_ADDRESS, amount * 100)
        print("Waiting for allowance to be set...")
        while True:
            new_allowance = await client.get_allowance(USDC_ADDRESS, EXCHANGE_ADDRESS)
            if new_allowance >= amount:
                break
            await asyncio.sleep(1)

async def place_order(client, signed_order, amount):
    try:
        await check_and_fix_allowance(client, amount)
        resp = client.post_order(signed_order)
        return resp
    except Exception as e:
        print(f"Error: {e}")
        return None

async def main():
    client = create_clob_client()  # Now this should work with the import
    amount = 30
    
    # You'll also need your signed order creation code here
    # signed_order = ... 
    
    result = await place_order(client, signed_order, amount)
    print(f"Order result: {result}")

if __name__ == "__main__":
    asyncio.run(main())