from decimal import Decimal
from typing import Dict, cast

from aiohttp import web
from pydantic import BaseModel, ConstrainedDecimal, conint, constr

from .bitcoin import MIN_RELAY_FEE, InsufficientFunds, create_unsigned_transaction, is_valid_address
from .config import settings
from .utils import error_response, json_response, validate_request

BitcoinAddress: constr = constr(min_length=1, max_length=100)


class BitcoinAmount(ConstrainedDecimal):
    gt = Decimal(0)
    decimal_places = 8


class CreateTransactionRequest(BaseModel):
    source_address: BitcoinAddress
    outputs: Dict[BitcoinAddress, BitcoinAmount]
    fee_kb: conint(ge=MIN_RELAY_FEE)  # type: ignore


@validate_request(CreateTransactionRequest)
async def create_transaction(_: web.Request, req_obj: CreateTransactionRequest) -> web.Response:
    if not req_obj.outputs:
        return error_response('empty_outputs', 'You have to specify at least one output')

    if not is_valid_address(req_obj.source_address):
        return error_response('invalid_source_address',
                              f'Please specify a valid source address (network: {settings.btc_network})')

    if req_obj.source_address[0] in {'2', '3'}:
        return error_response('unsupported_source_address', 'P2SH source addresses are not supported')

    invalid_outputs = []
    for output in req_obj.outputs.keys():
        if not is_valid_address(output):
            invalid_outputs.append(output)

    if invalid_outputs:
        return error_response('invalid_output_addresses',
                              f'Please specify a valid output addresses (network: {settings.btc_network})',
                              details={'invalid_addresses': invalid_outputs})

    try:
        tx_obj, inputs = await create_unsigned_transaction(
            source_address=req_obj.source_address,
            outputs_dict=cast(Dict[str, Decimal], req_obj.outputs),
            fee_kb=req_obj.fee_kb,
        )
    except InsufficientFunds as e:
        return error_response('insufficient_funds', str(e))

    return json_response({
        'raw': tx_obj.to_hex(),
        'inputs': [{
            'txid': u.txid,
            'vout': u.txindex,
            'script_pub_key': u.script,
            'amount': u.amount
        } for u in inputs],
    }, status=201)


async def make_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.post('/payment_transactions', create_transaction),
    ])
    return app


def run_app() -> None:
    web.run_app(make_app(), host='0.0.0.0', port=settings.port)
