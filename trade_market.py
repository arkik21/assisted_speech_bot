from typing import Literal
from py_clob_client.clob_types import  OrderArgs
from clob_client import create_clob_client

def create_and_submit_order(token_id: str, side: Literal['BUY'] | Literal['SELL'], price: float, size: int):
    client = create_clob_client()

    order_args = OrderArgs(
        price=price,
        size=size,
        side=side,
        token_id=token_id,
    )
    signed_order = client.create_order(order_args)
    resp = client.post_order(signed_order)
    print(resp)
    print('Done!')

# Will Trump say "Greenland" during victory rally? (10 shares)
create_and_submit_order('34510344541365974726107691584398341159796505768592867142296638107609795066241', 'SELL', 0.5, 35)


