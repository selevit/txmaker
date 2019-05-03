from decimal import Decimal
from typing import Dict, List, Tuple

import aiohttp
import bit.exceptions
from bit.constants import LOCK_TIME, VERSION_2
from bit.format import get_version
from bit.transaction import TxIn, construct_outputs
from bit.utils import hex_to_bytes
from bit.wallet import sanitize_tx_data

from .config import settings


class Unspent(bit.wallet.Unspent):
    pass


class InsufficientFunds(bit.exceptions.InsufficientFunds):
    pass


class TxObj(bit.transaction.TxObj):
    pass


async def create_unsigned_transaction(source_address: str, outputs: Dict[str, Decimal],
                                      fee_kb: int) -> Tuple[TxObj, List[Unspent]]:
    all_utxos = await get_unspent(source_address)
    confirmed_utxos = [u for u in all_utxos if u.confirmations >= settings.min_confirmations]
    if not confirmed_utxos:
        raise InsufficientFunds

    try:
        unspents, outputs = sanitize_tx_data(
            confirmed_utxos,
            [(address, amount, 'btc') for address, amount in outputs.items()],
            int(fee_kb / 1000),
            source_address,
            min_change=5461,
            version=settings.btc_network,
            combine=False,
        )
    except bit.exceptions.InsufficientFunds as e:
        raise InsufficientFunds from e

    version = VERSION_2
    lock_time = LOCK_TIME
    outputs = construct_outputs(outputs)
    inputs = []

    for unspent in unspents:
        script_sig = b''
        txid = hex_to_bytes(unspent.txid)[::-1]
        txindex = unspent.txindex.to_bytes(4, byteorder='little')
        amount = int(unspent.amount).to_bytes(8, byteorder='little')
        inputs.append(TxIn(script_sig, txid, txindex, amount=amount))

    tx_unsigned = TxObj(version, inputs, outputs, lock_time)
    return tx_unsigned, unspents


async def get_unspent(address: str) -> List[Unspent]:
    url = settings.blockchain_info_base_url + '/unspent'

    async with aiohttp.ClientSession() as session:
        resp: aiohttp.ClientResponse = await session.get(url, params={'active': address})
        if resp.status == 500:
            return []
        elif resp.status != 200:
            raise ConnectionError
        resp_data = await resp.json()
    return [
            Unspent(amount=tx['value'],
                    confirmations=tx['confirmations'],
                    script=tx['script'],
                    txid=tx['tx_hash_big_endian'],
                    txindex=tx['tx_output_n'])
            for tx in resp_data['unspent_outputs']
        ]


def is_valid_address(bitcoin_address: str) -> bool:
    try:
        return get_version(bitcoin_address) == settings.btc_network
    except ValueError:
        return False
