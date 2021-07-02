import string
import random
import json
import time
import base58
from solana.account import Account 
from solana.rpc.api import Client
from metaplex.metadata import get_metadata
from cryptography.fernet import Fernet
from api.metaplex_api import MetaplexAPI

def test():
    account = Account()
    cfg = {
        "PRIVATE_KEY": base58.b58encode(account.secret_key()).decode("ascii"),
        "PUBLIC_KEY": str(account.public_key()),
        "DECRYPTION_KEY": Fernet.generate_key().decode("ascii"),
    }
    api = MetaplexAPI(cfg)
    api_endpoint = "https://api.devnet.solana.com/"
    client = Client(api_endpoint)
    client.request_airdrop(api.public_key, int(1e10))
    time.sleep(30)
    letters = string.ascii_uppercase
    name = ''.join([random.choice(letters) for i in range(32)])
    symbol = ''.join([random.choice(letters) for i in range(10)])
    print("Name:", name)
    print("Symbol:", symbol)
    deploy_response = json.loads(api.deploy(api_endpoint, name, symbol, skip_confirmation=False))
    print("Deploy:", deploy_response)
    assert deploy_response["status"] == 200
    contract = deploy_response.get("contract")
    print(get_metadata(client, contract))
    wallet = json.loads(api.wallet())
    address1 = wallet.get('address')
    encrypted_pk1 = api.cipher.encrypt(bytes(wallet.get('private_key')))
    topup_response = json.loads(api.topup(api_endpoint, address1, skip_confirmation=False))
    print(f"Topup {address1}:", topup_response)
    assert topup_response["status"] == 200
    mint_to_response = json.loads(api.mint(api_endpoint, contract, address1, "https://arweave.net/1eH7bZS-6HZH4YOc8T_tGp2Rq25dlhclXJkoa6U55mM/", skip_confirmation=False))
    print("Mint:", mint_to_response)
    assert mint_to_response["status"] == 200
    print(get_metadata(client, contract))
    wallet2 = json.loads(api.wallet())
    address2 = wallet2.get('address')
    encrypted_pk2 = api.cipher.encrypt(bytes(wallet2.get('private_key')))
    print(client.request_airdrop(api.public_key, int(1e10)))
    topup_response2 = json.loads(api.topup(api_endpoint, address2, skip_confirmation=False))
    print(f"Topup {address2}:", topup_response2)
    assert topup_response2["status"] == 200
    send_response = json.loads(api.send(api_endpoint, contract, address1, address2, encrypted_pk1, skip_confirmation=False))
    assert send_response["status"] == 200
    burn_response = json.loads(api.burn(api_endpoint, contract, address2, encrypted_pk2, skip_confirmation=False))
    print("Burn:", burn_response)
    assert burn_response["status"] == 200
    print("Success!")

if __name__ == "__main__":
    test()