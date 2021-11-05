import argparse
import string
import random
import json
import time
import base58
from solana.keypair import Keypair
from solana.rpc.api import Client
from metaplex.metadata import get_metadata
from cryptography.fernet import Fernet
from api.metaplex_api import MetaplexAPI

def await_full_confirmation(client, txn, max_timeout=60):
    if txn is None:
        return
    elapsed = 0
    while elapsed < max_timeout:
        sleep_time = 1
        time.sleep(sleep_time)
        elapsed += sleep_time
        resp = client.get_confirmed_transaction(txn)
        while 'result' not in resp:
            resp = client.get_confirmed_transaction(txn)
        if resp["result"]:
            print(f"Took {elapsed} seconds to confirm transaction {txn}")
            break

def test(api_endpoint="https://api.devnet.solana.com/"):
    keypair = Keypair()
    cfg = {
        "PRIVATE_KEY": base58.b58encode(keypair.seed).decode("ascii"),
        "PUBLIC_KEY": str(keypair.public_key),
        "DECRYPTION_KEY": Fernet.generate_key().decode("ascii"),
    }
    api = MetaplexAPI(cfg)
    client = Client(api_endpoint)
    resp = {}
    while 'result' not in resp:
        resp = client.request_airdrop(keypair.public_key, int(1e9))
    print("Request Airdrop:", resp)
    txn = resp['result']
    await_full_confirmation(client, txn)
    letters = string.ascii_uppercase
    name = ''.join([random.choice(letters) for i in range(32)])
    symbol = ''.join([random.choice(letters) for i in range(10)])
    print("Name:", name)
    print("Symbol:", symbol)
    # added seller_basis_fee_points
    deploy_response = json.loads(api.deploy(api_endpoint, name, symbol, 0))
    print("Deploy:", deploy_response)
    assert deploy_response["status"] == 200
    contract = deploy_response.get("contract")
    print(get_metadata(client, contract))
    wallet = json.loads(api.wallet())
    address1 = wallet.get('address')
    encrypted_pk1 = api.cipher.encrypt(bytes(wallet.get('private_key')))
    topup_response = json.loads(api.topup(api_endpoint, address1))
    print(f"Topup {address1}:", topup_response)
    assert topup_response["status"] == 200
    mint_to_response = json.loads(api.mint(api_endpoint, contract, address1, "https://arweave.net/1eH7bZS-6HZH4YOc8T_tGp2Rq25dlhclXJkoa6U55mM/"))
    print("Mint:", mint_to_response)
    # await_confirmation(client, mint_to_response['tx'])
    assert mint_to_response["status"] == 200
    print(get_metadata(client, contract))
    wallet2 = json.loads(api.wallet())
    address2 = wallet2.get('address')
    encrypted_pk2 = api.cipher.encrypt(bytes(wallet2.get('private_key')))
    print(client.request_airdrop(api.public_key, int(1e10)))
    topup_response2 = json.loads(api.topup(api_endpoint, address2))
    print(f"Topup {address2}:", topup_response2)
    # await_confirmation(client, topup_response2['tx'])
    assert topup_response2["status"] == 200
    send_response = json.loads(api.send(api_endpoint, contract, address1, address2, encrypted_pk1))
    assert send_response["status"] == 200
    # await_confirmation(client, send_response['tx'])
    burn_response = json.loads(api.burn(api_endpoint, contract, address2, encrypted_pk2))
    print("Burn:", burn_response)
    # await_confirmation(client, burn_response['tx'])
    assert burn_response["status"] == 200
    print("Success!")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default=None)
    args = ap.parse_args()
    if args.network == None or args.network == 'devnet':
        test()
    elif args.network == 'testnet':
        test(api_endpoint="https://api.testnet.solana.com/")
    elif args.network == 'mainnet':
        test(api_endpoint="https://api.mainnet-beta.solana.com/")
    else:
        print("Invalid network argument supplied")
