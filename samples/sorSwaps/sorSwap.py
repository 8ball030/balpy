"""
Example of the sor swaps module usage.
"""


from datetime import datetime
from rich import print
from web3 import Web3
from third_party.forks.balpy.balpy.balpy import balpy

TZ = datetime.now().astimezone().tzinfo
DEFAULT_ENCODING = "utf-8"
DEFAULT_KEYPATH = "ethereum_private_key.txt"

rpcs = {
    "base": "https://base.drpc.org",
}

def setup_balpy(key_path, network: str = 'base') -> balpy:
    """Set up balpy."""
    with open(key_path, encoding=DEFAULT_ENCODING) as file:
        key = file.read().strip()
    bal: balpy = balpy(
        network,
        manualEnv={
            "privateKey": key,
            "customRPC": rpcs[network],
            "etherscanApiKey": '0x123',
        },
    )
    return bal


def get_ticker_sor_data(
        bal: balpy,
        quote_asset: str,
        base_asset: str,
        amount: float) -> None:
    """Get buy and sell transactions."""

    orderBookData = bal.graph.getTicker(
        bal.network,
        base_asset,
        quote_asset,
        amount,
    )
    return orderBookData


def get_params_for_swap(
    bal: balpy,
    input_token_address: str,
    output_token_address: str,
    input_amount: float,
    is_buy: bool = False,
    slippage: float = 0.000000001,
    sender_address: str | None = None,
) -> dict:
    """Given the data, we get the params for the swap from the balancer exchange."""
    gas_price = bal.web3.eth.gas_price * 2

    # Use sender_address if provided, otherwise fall back to account address
    address_to_use = sender_address

    return {
        "network": bal.network,
        "slippageTolerancePercent": str(slippage),
        "sor": {
            "sellToken": input_token_address,
            "buyToken": output_token_address,  # // token out
            "orderKind": "buy" if is_buy else "sell",
            "amount": input_amount,
            "gasPrice": gas_price,
        },
        "batchSwap": {
            "funds": {
                "sender": address_to_use,  # Uses provided address or default
                "recipient": address_to_use,  # Uses provided address or default
                "fromInternalBalance": False,  # // to/from internal balance
                "toInternalBalance": False,  # // set to "false" unless you know what you're doing
            },
            # // unix timestamp after which the trade will revert if it hasn't executed yet
            "deadline": datetime.now(tz=TZ).timestamp() + 600,
        },
    }

def parse_book_data(data,
                    bal: balpy,
                    quote_asset: str,
                    base_asset: str,
                    amount: float
                    ) -> dict:
    """Parse book data."""
    actual_buy_rate, buy_mc_args = get_buy_rate(
        bal=bal,
        quote_asset=quote_asset,
        base_asset=base_asset,
        amount=amount,
        sor_data=data,
    )
    actual_sell_rate, sell_mc_args = get_sell_rate(
        bal=bal,
        quote_asset=quote_asset,
        base_asset=base_asset,
        amount=amount,
        sor_data=data,
    )
    data['buy_mc_args'] = buy_mc_args
    data['sell_mc_args'] = sell_mc_args
    data['actual_buy_rate'] = actual_buy_rate
    data['actual_sell_rate'] = actual_sell_rate
    return data


def get_buy_rate(
    bal: balpy,
    quote_asset: str,
    base_asset: str,
    amount: float,
    sender_address: str | None = None,
    sor_data: dict | None = None,
) -> float:
    """Perform a buy of base asset with quote asset."""
    print("Processing buy of 100 OLAS with USDC")
    params = get_params_for_swap(
        bal=bal,
        input_token_address=quote_asset,
        output_token_address=base_asset,
        input_amount=amount,
        is_buy=True,
        sender_address=sender_address or bal.address,
    )
    batch_swap = bal.balSorResponseToBatchSwapFormat(params, sor_data.get("ask")).get("batchSwap", None)
    mc_args = bal.balFormatBatchSwapData(batch_swap)
    # retrieve the actual rate from the limits
    limits = mc_args[-2]
    in_amt, out_amt = min(limits), max(limits)
    input_amount = -in_amt * 10 ** -bal.erc20GetDecimals(base_asset) 
    output_amount = out_amt * 10 ** -bal.erc20GetDecimals(quote_asset)
    real_rate =  output_amount / input_amount
    return real_rate, mc_args



def get_sell_rate(
    bal: balpy,
    quote_asset: str,
    base_asset: str,
    amount: float,
    sender_address: str | None = None,
    sor_data: dict | None = None,
) -> None:
    """Perform a sell of base asset for quote asset."""
    print("Processing sell of 100 OLAS with USDC")
    
    params = get_params_for_swap(
        bal=bal,
        input_token_address=base_asset,
        output_token_address=quote_asset,
        input_amount=amount,
        is_buy=False,
        sender_address=sender_address or bal.address,
    )

    batch_swap = bal.balSorResponseToBatchSwapFormat(params, sor_data.get("bid")).get("batchSwap", None)
    mc_args = bal.balFormatBatchSwapData(batch_swap)
    limits = mc_args[-2]
    in_amt, out_amt = min(limits), max(limits)
    input_amount = in_amt * 10 ** -bal.erc20GetDecimals(quote_asset)
    output_amount = -out_amt * 10 ** -bal.erc20GetDecimals(base_asset)
    real_rate = input_amount /output_amount
    return real_rate, mc_args



def build_swap(
    bal: balpy,
    mc_args,
) -> None:
    """Perform a batch swap."""
    vault = bal.balLoadContract('Vault')
    return vault.functions.batchSwap(*mc_args)

def sign_and_send_transaction(
    bal: balpy,
    function_call,
    ) -> None:
    """Sign and send a transaction."""
    print("Signing and sending transaction...")
    tx = bal.buildTx(function_call, gasFactor=1.2)
    tx_hash = bal.sendTx(tx)
    print(f"Transaction hash: {tx_hash}")



if __name__ == "__main__":
    bal = setup_balpy(DEFAULT_KEYPATH, network='base')
    quote_asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC
    base_asset="0x9d0E8f5b25384C7310CB8C6aE32C8fbeb645d083"  # DRV
    base_asset="0x54330d28ca3357F294334BDC454a032e7f353416"  # OLAS
    amount=10

    book_data = get_ticker_sor_data(
        bal,
        quote_asset=quote_asset,
        base_asset=base_asset,
        amount=amount,
    )

    order_data = parse_book_data(
        data=book_data,
        bal=bal,
        quote_asset=quote_asset,
        base_asset=base_asset,
        amount=amount,
    )
    print(f"Processing buy of {amount} OLAS with USDC")
    function = build_swap(
        bal=bal,
        mc_args=order_data['buy_mc_args'],
    )
    cost = order_data['actual_buy_rate'] * amount
    print(f"Cost of buy: {cost} USDC")
    if input("Proceed with buy? (y/n): ") == "y":
        sign_and_send_transaction(
            bal=bal,
            function_call=function,
        )
    
    print(f"Processing sell of {amount} OLAS with USDC")
    received = order_data['actual_sell_rate'] * amount
    print(f"Received from sell: {received} USDC")
    function = build_swap(
        bal=bal,
        mc_args=order_data['sell_mc_args'],
    )
    if input("Proceed with sell? (y/n): ") == "y":
        sign_and_send_transaction(
            bal=bal,
            function_call=function,
        )
    print("Done.")






