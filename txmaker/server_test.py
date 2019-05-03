from typing import Any

from aiohttp import web
from aiohttp.test_utils import TestClient


async def test_create_transaction_invalid_request(client: TestClient) -> None:
    response = await client.post('/payment_transactions', data='invalid json')
    assert response.status == 400


async def test_create_transaction_with_negative_amounts(client: TestClient) -> None:
    response = await client.post('/payment_transactions', json={
        "source_address": "mfetsqmVYU1m3w1MNXaDg4cvGYwXJB47Kx",
        "outputs": {
            "mhnnkpnCfBkxN5KpfMArye2F376nATVJDW": "-0.0001",
            "mvDvYba71W8at5sU9G8ELqQph8s7fKgbiA": "0.002",
            "msrXsFAeRMLnY9mGPyeVwZZqxqVQUXh4uh": "0.02"
        },
        "fee_kb": 25000
    })
    assert response.status == 400
    response_data = await response.json()
    assert response_data['error']['code'] == 'invalid_request_schema'


async def test_create_transaction_with_negative_fee(client: TestClient) -> None:
    response = await client.post('/payment_transactions', json={
        "source_address": "mfetsqmVYU1m3w1MNXaDg4cvGYwXJB47Kx",
        "outputs": {
            "mhnnkpnCfBkxN5KpfMArye2F376nATVJDW": "-0.0001",
        },
        "fee_kb": -1
    })
    assert response.status == 400
    response_data = await response.json()
    assert response_data['error']['code'] == 'invalid_request_schema'


async def test_create_transaction_with_invalid_amount_precision_input(client: TestClient) -> None:
    response = await client.post('/payment_transactions', json={
        "source_address": "mfetsqmVYU1m3w1MNXaDg4cvGYwXJB47Kx",
        "outputs": {
            "mvDvYba71W8at5sU9G8ELqQph8s7fKgbiA": "0.000000001",
            "msrXsFAeRMLnY9mGPyeVwZZqxqVQUXh4uh": "0.02"
        },
        "fee_kb": 25000
    })
    assert response.status == 400
    response_data = await response.json()
    assert response_data['error']['code'] == 'invalid_request_schema'


async def test_create_transaction_with_empty_outputs(client: TestClient) -> None:
    response = await client.post('/payment_transactions', json={
        "source_address": "mfetsqmVYU1m3w1MNXaDg4cvGYwXJB47Kx",
        "outputs": {},
        "fee_kb": 25000,
    })
    assert response.status == 400
    response_data = await response.json()
    assert response_data['error']['code'] == 'empty_outputs'


async def test_create_if_no_available_utxos(client: TestClient, mock_unspent_response: Any) -> None:
    await mock_unspent_response(web.Response(body='No free outputs to spend', status=500))

    response = await client.post('/payment_transactions', json={
        "source_address": "mfetsqmVYU1m3w1MNXaDg4cvGYwXJB47Kx",
        "outputs": {"mhnnkpnCfBkxN5KpfMArye2F376nATVJDW": "0.0001"},
        "fee_kb": 25000
    })

    assert response.status == 400
    response_data = await response.json()
    assert response_data['error']['code'] == 'insufficient_funds'
    assert response_data['error']['message'] == 'No confirmed UTXOs were found'


async def test_create_if_no_available_confirmed_utxos(client: TestClient, mock_unspent_response: Any) -> None:
    await mock_unspent_response(web.json_response({
        "unspent_outputs": [{
            "tx_hash": "0bb4abea99101197cf2ddf43a2af1e73f868887d5f4a3619241cbb67413a34e7",
            "tx_hash_big_endian": "e7343a4167bb1c2419364a5f7d8868f8731eafa243df2dcf97111099eaabb40b",
            "tx_index": 298994538,
            "tx_output_n": 3,
            "script": "76a9140180799618375ebd21bd67014deca9a167b8f91e88ac",
            "value": 13000000,
            "value_hex": "00c65d40",
            "confirmations": 5
        }]
    }))

    response = await client.post('/payment_transactions', json={
        "source_address": "mfetsqmVYU1m3w1MNXaDg4cvGYwXJB47Kx",
        "outputs": {"mhnnkpnCfBkxN5KpfMArye2F376nATVJDW": "0.0001"},
        "fee_kb": 25000
    })

    response_data = await response.json()
    assert response.status == 400
    assert response_data['error']['code'] == 'insufficient_funds'
    assert response_data['error']['message'] == 'No confirmed UTXOs were found'


async def test_create_transaction_if_invalid_source_address(client: TestClient) -> None:
    response = await client.post('/payment_transactions', json={
        "source_address": "bad0000000000000000000000000000000",
        "outputs": {"mhnnkpnCfBkxN5KpfMArye2F376nATVJDW": "0.0001"},
        "fee_kb": 25000
    })
    response_data = await response.json()
    assert response.status == 400
    assert response_data['error']['code'] == 'invalid_source_address'


async def test_create_transaction_if_invalid_output_address(client: TestClient) -> None:
    response = await client.post('/payment_transactions', json={
        "source_address": "mhnnkpnCfBkxN5KpfMArye2F376nATVJDW",
        "outputs": {
            "mhnnkpnCfBkxN5KpfMArye2F376nATVJDW": "0.0001",
            "bad0000000000000000000000000000000": "100.0",
            "bad2": "100.0",
        },
        "fee_kb": 25000
    })
    response_data = await response.json()
    assert response.status == 400
    assert response_data['error']['code'] == 'invalid_output_addresses'
    assert response_data['error']['details']['invalid_addresses'] == ['bad0000000000000000000000000000000', 'bad2']


async def test_create_transaction_if_insufficient_funds(client: TestClient, mock_unspent_response: Any) -> None:
    await mock_unspent_response(web.json_response({
        "unspent_outputs": [
            {
                "tx_hash": "0bb4abea99101197cf2ddf43a2af1e73f868887d5f4a3619241cbb67413a34e7",
                "tx_hash_big_endian": "e7343a4167bb1c2419364a5f7d8868f8731eafa243df2dcf97111099eaabb40b",
                "tx_index": 298994538,
                "tx_output_n": 3,
                "script": "76a9140180799618375ebd21bd67014deca9a167b8f91e88ac",
                "value": 13000000,
                "value_hex": "00c65d40",
                "confirmations": 6,
            },
        ]
    }))

    response = await client.post('/payment_transactions', json={
        "source_address": "mfetsqmVYU1m3w1MNXaDg4cvGYwXJB47Kx",
        "outputs": {"mhnnkpnCfBkxN5KpfMArye2F376nATVJDW": "20"},
        "fee_kb": 25000
    })

    assert response.status == 400
    response_data = await response.json()
    assert response_data['error']['code'] == 'insufficient_funds'
    assert response_data['error']['message'] == 'Balance 13000000 is less than 2000005650 (including fee).'


async def test_create_transaction_with_p2sh_input(client: TestClient) -> None:
    response = await client.post('/payment_transactions', json={
        "source_address": "2NA4VVsS4jperVT5HfnaLNYKn15oeehvutJ",
        "outputs": {
            "2MtDYVRt3Wdp2sDadhLnPoXDrzsTsBXq5c7": "0.0001",
            "mvDvYba71W8at5sU9G8ELqQph8s7fKgbiA": "0.002",
            "msrXsFAeRMLnY9mGPyeVwZZqxqVQUXh4uh": "0.02"
        },
        "fee_kb": 25000
    })
    assert response.status == 400
    response_data = await response.json()
    assert response_data['error']['code'] == 'unsupported_source_address'


async def test_create_transaction_if_both_p2sh_and_p2pkh_outputs(client: TestClient,
                                                                 mock_unspent_response: Any) -> None:
    await mock_unspent_response(web.json_response({
        "unspent_outputs": [{
            "tx_hash": "0bb4abea99101197cf2ddf43a2af1e73f868887d5f4a3619241cbb67413a34e7",
            "tx_hash_big_endian": "e7343a4167bb1c2419364a5f7d8868f8731eafa243df2dcf97111099eaabb40b",
            "tx_index": 298994538,
            "tx_output_n": 3,
            "script": "76a9140180799618375ebd21bd67014deca9a167b8f91e88ac",
            "value": 13000000,
            "value_hex": "00c65d40",
            "confirmations": 6
        }]
    }))
    response = await client.post('/payment_transactions', json={
        "source_address": "mfetsqmVYU1m3w1MNXaDg4cvGYwXJB47Kx",
        "outputs": {
            "2MtDYVRt3Wdp2sDadhLnPoXDrzsTsBXq5c7": "0.0001",
            "mvDvYba71W8at5sU9G8ELqQph8s7fKgbiA": "0.002",
            "msrXsFAeRMLnY9mGPyeVwZZqxqVQUXh4uh": "0.02"
        },
        "fee_kb": 25000
    })

    assert response.status == 201
    response_data = await response.json()
    assert response_data == {
        'raw': '02000000010bb4abea99101197cf2ddf43a2af1e73f868887d5f4a3619241cbb67413a34e70300000000fffff'
               'fff04102700000000000017a9140aa6bd2de1acdfa92e4c932a4850a3883381402b87400d0300000000001976'
               'a914a1515aee272e49cd1e2f9c3490743c4b232d265088ac80841e00000000001976a91487556ff8cc729dd74'
               '3ee7bf33302098135b95c5e88acec87a400000000001976a9140180799618375ebd21bd67014deca9a167b8f91'
               'e88ac00000000',
        'inputs': [
            {
                'txid': 'e7343a4167bb1c2419364a5f7d8868f8731eafa243df2dcf97111099eaabb40b',
                'vout': 3, 'script_pub_key': '76a9140180799618375ebd21bd67014deca9a167b8f91e88ac',
                'amount': 13000000
            }
        ]
    }


async def test_create_transaction_if_no_change(client: TestClient,  mock_unspent_response: Any) -> None:
    await mock_unspent_response(web.json_response({
        "unspent_outputs": [
            {
                "tx_hash": "d0ecaa87d4629a59480d6b156e646a05010d244455fcb7d87af9ecc052fa0264",
                "tx_hash_big_endian": "6402fa52c0ecf97ad8b7fc5544240d01056a646e156b0d48599a62d487aaecd0",
                "tx_index": 197282253,
                "tx_output_n": 0,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 12982733,
                "value_hex": "00c619cd",
                "confirmations": 163637
            },
        ]
    }))
    response = await client.post('/payment_transactions', json={
        "source_address": "mqdofsXHpePPGBFXuwwypAqCcXi48Xhb2f",
        "outputs": {
            "mhnnkpnCfBkxN5KpfMArye2F376nATVJDW": "0.12976851",
        },
        "fee_kb": 2000
    })

    assert response.status == 201
    response_data = await response.json()
    assert response_data == {
        'raw': '0200000001d0ecaa87d4629a59480d6b156e646a05010d244455fcb7d87af9ecc052fa02640000000000ffffff'
               'ff01d302c600000000001976a91418eef1d5d14e8032ca7caacefce7164179320b9388ac00000000',
        'inputs': [
            {
                'txid': '6402fa52c0ecf97ad8b7fc5544240d01056a646e156b0d48599a62d487aaecd0',
                'vout': 0, 'script_pub_key': '76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac',
                'amount': 12982733
            }
        ]
    }


async def test_create_transaction_with_many_inputs(client: TestClient, mock_unspent_response: Any) -> None:
    await mock_unspent_response(web.json_response({
        "unspent_outputs": [
            {
                "tx_hash": "13e1ce6d1803b46963871e89f768de93fdef7b86e820e1abd70c400dadeb1671",
                "tx_hash_big_endian": "7116ebad0d400cd7abe120e8867beffd93de68f7891e876369b403186dcee113",
                "tx_index": 197282181,
                "tx_output_n": 1,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 45581249,
                "value_hex": "02b783c1",
                "confirmations": 163638
            },
            {
                "tx_hash": "d0ecaa87d4629a59480d6b156e646a05010d244455fcb7d87af9ecc052fa0264",
                "tx_hash_big_endian": "6402fa52c0ecf97ad8b7fc5544240d01056a646e156b0d48599a62d487aaecd0",
                "tx_index": 197282253,
                "tx_output_n": 0,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 12982733,
                "value_hex": "00c619cd",
                "confirmations": 163637
            },
            {
                "tx_hash": "14f2fcb8b5344c1c31edb2d3064b52d87255b548eae56692ccb89387b75280ce",
                "tx_hash_big_endian": "ce8052b78793b8cc9266e5ea48b55572d8524b06d3b2ed311c4c34b5b8fcf214",
                "tx_index": 197306298,
                "tx_output_n": 0,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 930000,
                "value_hex": "0e30d0",
                "confirmations": 163544
            },
            {
                "tx_hash": "af56d16f2e59315e1a49b73005d48e1faccefc323122797b0c0588187bc5a0a1",
                "tx_hash_big_endian": "a1a0c57b1888050c7b79223132fcceac1f8ed40530b7491a5e31592e6fd156af",
                "tx_index": 197586654,
                "tx_output_n": 0,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 894094,
                "value_hex": "0da48e",
                "confirmations": 162639
            },
            {
                "tx_hash": "fda33a301cfd9f0c324a96dfccaa4057127b274868a336fd313542a187d37e48",
                "tx_hash_big_endian": "487ed387a1423531fd36a36848277b125740aaccdf964a320c9ffd1c303aa3fd",
                "tx_index": 197306217,
                "tx_output_n": 0,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 930000,
                "value_hex": "0e30d0",
                "confirmations": 163544
            },
            {
                "tx_hash": "c30fe13d1c77f5a31eff19a452b19dd970e9716897c78ea57b7f1e2d96e6fb0e",
                "tx_hash_big_endian": "0efbe6962d1e7f7ba58ec7976871e970d99db152a419ff1ea3f5771c3de10fc3",
                "tx_index": 197307258,
                "tx_output_n": 0,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 930000,
                "value_hex": "0e30d0",
                "confirmations": 163535
            },
            {
                "tx_hash": "276f505fe884ec4697a7a82f001012e235896a3b309ce13a3faf036a504f4209",
                "tx_hash_big_endian": "09424f506a03af3f3ae19c303b6a8935e21210002fa8a79746ec84e85f506f27",
                "tx_index": 197343492,
                "tx_output_n": 1,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 46447811,
                "value_hex": "02c4bcc3",
                "confirmations": 163388
            },
            {
                "tx_hash": "179a1cfd5e5a19747478461ea57f76b727a16f96254f79fba0dcd30e1029f551",
                "tx_hash_big_endian": "51f529100ed3dca0fb794f25966fa127b7767fa51e46787474195a5efd1c9a17",
                "tx_index": 197343459,
                "tx_output_n": 1,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 4382812,
                "value_hex": "42e05c",
                "confirmations": 163388
            },
            {
                "tx_hash": "c1ad8c931707999f5e0cbfe504c3dc772907901d4001a517e567757fae2f7f2d",
                "tx_hash_big_endian": "2d7f2fae7f7567e517a501401d90072977dcc304e5bf0c5e9f990717938cadc1",
                "tx_index": 197378103,
                "tx_output_n": 0,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 1025703,
                "value_hex": "0fa6a7",
                "confirmations": 163290
            },
            {
                "tx_hash": "6287fd705063d962a2006c0b5f9fc65f0e6a5ba62783a2d9e3d9b27bad91ff97",
                "tx_hash_big_endian": "97ff91ad7bb2d9e3d9a28327a65b6a0e5fc69f5f0b6c00a262d9635070fd8762",
                "tx_index": 197378271,
                "tx_output_n": 1,
                "script": "76a9146efcf883b4b6f9997be9a0600f6c095fe2bd2d9288ac",
                "value": 49989634,
                "value_hex": "02fac802",
                "confirmations": 163289
            },
        ]
    }))

    response = await client.post('/payment_transactions', json={
        "source_address": "mqdofsXHpePPGBFXuwwypAqCcXi48Xhb2f",
        "outputs": {
            "mhnnkpnCfBkxN5KpfMArye2F376nATVJDW": "0.0001",
            "2MtDYVRt3Wdp2sDadhLnPoXDrzsTsBXq5c7": "0.002",
            "msrXsFAeRMLnY9mGPyeVwZZqxqVQUXh4uh": "0.02"
        },
        "fee_kb": 25000
    })

    assert response.status == 201


async def test_create_transaction_with_p2pkh_output(client: TestClient, mock_unspent_response: Any) -> None:
    await mock_unspent_response(web.json_response({
        "unspent_outputs": [{
            "tx_hash": "0bb4abea99101197cf2ddf43a2af1e73f868887d5f4a3619241cbb67413a34e7",
            "tx_hash_big_endian": "e7343a4167bb1c2419364a5f7d8868f8731eafa243df2dcf97111099eaabb40b",
            "tx_index": 298994538,
            "tx_output_n": 3,
            "script": "76a9140180799618375ebd21bd67014deca9a167b8f91e88ac",
            "value": 13000000,
            "value_hex": "00c65d40",
            "confirmations": 6
        }]
    }))

    response = await client.post('/payment_transactions', json={
        "source_address": "mfetsqmVYU1m3w1MNXaDg4cvGYwXJB47Kx",
        "outputs": {
            "mhnnkpnCfBkxN5KpfMArye2F376nATVJDW": "0.0001",
            "mvDvYba71W8at5sU9G8ELqQph8s7fKgbiA": "0.002",
            "msrXsFAeRMLnY9mGPyeVwZZqxqVQUXh4uh": "0.02"
        },
        "fee_kb": 25000
    })

    assert response.status == 201
    response_data = await response.json()

    assert response_data == {
        'raw': '02000000010bb4abea99101197cf2ddf43a2af1e73f868887d5f4a3619241cbb67413a34e70300000000fffff'
               'fff0410270000000000001976a91418eef1d5d14e8032ca7caacefce7164179320b9388ac400d0300000000001'
               '976a914a1515aee272e49cd1e2f9c3490743c4b232d265088ac80841e00000000001976a91487556ff8cc729dd'
               '743ee7bf33302098135b95c5e88acba87a400000000001976a9140180799618375ebd21bd67014deca9a167b8f9'
               '1e88ac00000000',
        'inputs': [
            {
                'txid': 'e7343a4167bb1c2419364a5f7d8868f8731eafa243df2dcf97111099eaabb40b',
                'vout': 3, 'script_pub_key': '76a9140180799618375ebd21bd67014deca9a167b8f91e88ac',
                'amount': 13000000
            }
        ]
    }
