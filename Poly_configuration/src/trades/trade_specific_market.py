from typing import Literal

from py_clob_client.clob_types import  OrderArgs

from helpers.clob_client import create_clob_client


def create_and_submit_order(token_id: str, side: Literal['BUY'] | Literal['SELL'], price: float, size: int):
    client = create_clob_client()

    # Create and sign a limit order buying 100 YES tokens for 0.0005 each
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
