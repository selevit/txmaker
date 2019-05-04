import math
from decimal import Decimal
from typing import Dict, List, Tuple

import aiohttp
import bit.exceptions
from bit.constants import LOCK_TIME, VERSION_2
from bit.format import get_version
from bit.transaction import TxIn, address_to_scriptpubkey, construct_outputs, int_to_unknown_bytes
from bit.utils import hex_to_bytes

from .config import settings

DUST_THRESHOLD = 5430
SATOSHI_MULTIPLIER = Decimal('1e8')
MIN_RELAY_FEE = 1000


# wrap the bit package's objects into our owns
# in order to encapsulate all bitcoin abstractions in this module
class Unspent(bit.wallet.Unspent):
    pass


class TxObj(bit.transaction.TxObj):
    pass


class InsufficientFunds(bit.exceptions.InsufficientFunds):
    pass


Output = Tuple[str, int]


def estimate_tx_size(n_in: int, in_size: int, n_out: int, out_size: int) -> int:
    """
    Calculates an estimated transaction size (in bytes)
    """
    return (
        in_size
        + len(int_to_unknown_bytes(n_in, byteorder='little'))
        + out_size
        + len(int_to_unknown_bytes(n_out, byteorder='little'))
        + 8
    )


def calc_in_size(n_in: int) -> int:
    return 148 * n_in


def calc_out_size(addresses: List[str]) -> int:
    return sum(len(address_to_scriptpubkey(o)) + 9 for o in addresses)


def estimate_tx_fee(n_in: int, in_size: int, n_out: int, out_size: int, fee_kb: int) -> int:
    """
    Calculates estimated transaction fee (in satoshi)
    fee_kb measures in satoshi per 1000 bytes
    """
    assert fee_kb >= MIN_RELAY_FEE
    size = estimate_tx_size(n_in, in_size, n_out, out_size)
    return math.ceil(size * fee_kb * 0.001)


def select_unspents(source_address: str, unspents: List[Unspent],
                    outputs: List[Output], fee_kb: int) -> Tuple[List[Unspent], int]:
    out_addresses = []
    out_amount = 0

    for addr, amount in outputs:
        out_addresses.append(addr)
        out_amount += amount

    n_out = len(out_addresses) + 1
    out_size = calc_out_size(out_addresses + [source_address])

    selected_inputs: List[Unspent] = []
    spending_amount = 0

    for u in unspents:
        spending_amount += u.amount
        selected_inputs.append(u)
        n_in = len(selected_inputs)
        in_size = calc_in_size(n_in)
        fee = estimate_tx_fee(n_in, in_size, n_out, out_size, fee_kb)
        if out_amount + fee <= spending_amount:
            break
    else:
        balance = sum(u.amount for u in selected_inputs)
        raise InsufficientFunds(f'Balance {balance} is less than {out_amount+fee} (including fee)')

    return selected_inputs, spending_amount - (out_amount+fee)


async def create_unsigned_transaction(source_address: str, outputs_dict: Dict[str, Decimal],
                                      fee_kb: int) -> Tuple[TxObj, List[Unspent]]:
    all_utxos = await get_unspent(source_address)
    confirmed_utxos = [u for u in all_utxos if u.confirmations >= settings.min_confirmations]

    if not confirmed_utxos:
        raise InsufficientFunds('No confirmed UTXOs were found')

    outputs = [(addr, int(amount * SATOSHI_MULTIPLIER)) for addr, amount in outputs_dict.items()]
    inputs, change_amount = select_unspents(source_address, confirmed_utxos, outputs, fee_kb)

    if change_amount > DUST_THRESHOLD:
        outputs.append((source_address, change_amount))

    version = VERSION_2
    lock_time = LOCK_TIME
    raw_outputs = construct_outputs(outputs)
    raw_inputs = []

    for unspent in inputs:
        script_sig = b''
        txid = hex_to_bytes(unspent.txid)[::-1]
        txindex = unspent.txindex.to_bytes(4, byteorder='little')
        amount = int(unspent.amount).to_bytes(8, byteorder='little')
        raw_inputs.append(TxIn(script_sig, txid, txindex, amount=amount))

    tx_unsigned = TxObj(version, raw_inputs, raw_outputs, lock_time)
    return tx_unsigned, inputs


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
        ][::-1]  # oldest first


def is_valid_address(bitcoin_address: str) -> bool:
    try:
        return get_version(bitcoin_address) == settings.btc_network
    except ValueError:
        return False
