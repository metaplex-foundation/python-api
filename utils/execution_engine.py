import time
from solana.account import Account 
from solana.rpc.api import Client

def execute(api_endpoint, tx, signers, max_retries=3, skip_confirmation=True, max_timeout=60, target=20, finalized=True):
    client = Client(api_endpoint)
    signers = list(map(Account, set(map(lambda s: s.secret_key(), signers))))
    for attempt in range(max_retries):
        try:
            result = client.send_transaction(tx, *signers)
            signatures = [x.signature for x in tx.signatures]
            if not skip_confirmation:
                await_confirmation(client, signatures, max_timeout, target, finalized)
            return result
        except Exception as e:
            print(f"Failed attempt {attempt}: {e}")
            continue
    raise e

def await_confirmation(client, signatures, max_timeout=60, target=20, finalized=True):
    elapsed = 0
    while elapsed < max_timeout:
        sleep_time = 1
        time.sleep(sleep_time)
        elapsed += sleep_time
        resp = client.get_signature_statuses(signatures)
        confirmations = resp["result"]["value"][0]["confirmations"]
        is_finalized = resp["result"]["value"][0]["confirmationStatus"] == "finalized"
        if not finalized:
            if confirmations >= target or is_finalized:
                print(f"Took {elapsed} seconds to confirm transaction")
                return
        elif is_finalized:
            print(f"Took {elapsed} seconds to confirm transaction")
            return