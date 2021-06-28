from enum import Enum
import json
import requests
from requests.api import head
import solana.public_key import PublicKey 
import solana.transaction import Transaction
import solana.account import Account 
import solana.system_program import transfer, TransferParams 
from spl.token.instructions import (
    mint_to, MintToParams, transfer as spl_transfer
)
import base58
from nacl.public import PrivateKey
from nacl import signing

Status = Enum("Success", "Failure")

def deploy(self, network, contract, name, symbol):
    """
    Deploy a contract to the blockchain (on networks that support contracts). Takes the network ID and contract name, plus initialisers of name and symbol. Process may vary significantly between blockchains.
    Returns status code of success or fail, the contract address, and the native transaction data.
    """
    status = None
    address = None
    tx = None
    # TODO
    # Perform blockchain operations
    return json.dumps(
        {
            'status': status,
            'address': address,
            'tx': tx,
        }
    )

def wallet(self, network):
    """ Generate a wallet on the specified network and return the address and private key. """
    private_key = PrivateKey.generate()
    address = base58.b58encode(signing.SigningKey(private_key.encode()).verify_key.encode())
    return json.dumps(
        {
            'address': address,
            'private_key': private_key.encode()
        }
    )

def topup(self, network, to, amount):
    """
    Send a small amount of native currency to the specified wallet to handle gas fees. Return a status flag of success or fail and the native transaction data.
    """
    try:
        client = Client("https://api.mainnet-beta.solana.com/")
        sender = Account(SOURCE_ACCOUNT_KEY) # Global variable from config file
        receiver = Account(to)
        signers = [sender, receiver]
        ix = transfer(TransferParams(from_pubkey=sender.public_key(), to_pubkey=receiver.public_key(), lamports=amount))
        tx = Transaction().add(ix, *signers)
        response = client.send_transaction(tx).json()
        if "error" not in response:
            return json.dumps(
                {
                    'status': Status.Success,
                    'tx': response['result']
                }
            )
    except:
        pass
    finally:
        return json.dumps(
            {
                'status': Status.Failure,
                'tx': tx
            }
        )

def mint(self, network, contract, address, batch, sequence, limit, name, description, link, created, content='', **kw):
    """
    Mint a token on the specified network and contract, into the wallet specified by address.
    Required parameters: batch, sequence, limit
    These are all 32-bit unsigned ints and are assembled into a 96-bit integer ID on Ethereum and compatible blockchains.
    Where this is not possible we'll look for an alternate mapping.

    Additional character fields: name, description, link, created
    These are text fields intended to be written directly to the blockchain. created is an ISO standard timestamp string (UTC)
    content is an optional JSON string for customer-specific data.
    Return a status flag of success or fail and the native transaction data.

    """
    tx = None
    try:
        client = Client("https://api.mainnet-beta.solana.com/")
        signers = [Account(SOURCE_ACCOUNT_KEY)]
        mint_to_params = MintToParams(
            program_id=PublicKey(TOKEN_PROGRAM_ID),
            mint=PublicKey(MINT_ACCOUNT_KEY),
            dest=PublicKey(address),
            owner=PublicKey(SOURCE_ACCOUNT_PUBKEY),
            signers=signers,
        )
        ix = mint_to(mint_to_params)
        tx = client.set_transaction(ix, *signers) 
        response = client.send_transaction(tx).json()
        if "error" not in response:
            return json.dumps(
                {
                    'status': Status.Success,
                    'tx': tx,
                }
            )
    except:
        pass
    finally:
        return json.dumps(
            {
                'status': Status.Failure,
                'tx': tx
            }
        )

def send(self, network, contract, sender, to, token, private_key, contract_address):
    """
    Transfer a token on a given network and contract from the sender to the recipient.
    May require a private key, if so this will be provided encrypted using Fernet: https://cryptography.io/en/latest/fernet/
    Return a status flag of success or fail and the native transaction data. 
    """
    tx = None
    try:
        client = Client(network)
        signers = [Account(SOURCE_ACCOUNT_KEY), Account(private_key)]
        spl_transfer_params = TransferParams(
            program_id=Pubkey(TOKEN_PROGRAM_ID),
            source=Pubkey(sender),
            dest=Pubkey(to),
            owner=Pubkey(SOURCE_ACCOUNT_PUBKEY),
            signers=signers,
        )
        ix = spl_transfer(spl_transfer_params)
        tx = client.set_transaction(ix, *signers) 
        response = client.send_transaction(tx).json()
        if "error" not in response:
            return json.dumps(
                {
                    'status': Status.Success,
                    'tx': tx,
                }
            )
    except:
        pass
    finally:
        return json.dumps(
            {
                'status': Status.Failure,
                'tx': tx
            }
        )

def burn(self, network, contract, sender, token, private_key, contract_address):
    """
    Burn a token, permanently removing it from the blockchain.
    May require a private key, if so this will be provided encrypted using Fernet: https://cryptography.io/en/latest/fernet/
    Return a status flag of success or fail and the native transaction data.
    """
    tx = None
    try:
        client = Client(network)
        signers = [Account(SOURCE_ACCOUNT_KEY), Account(private_key)]
        burn_params = BurnParams(
            program_id=Pubkey(TOKEN_PROGRAM_ID),
            account=Pubkey(sender),
            mint=PublicKey(MINT_ACCOUNT_KEY),
            owner=Pubkey(SOURCE_ACCOUNT_PUBKEY),
            amount=1,
            signers=signers,
        )
        ix = spl_transfer(burn_params)
        tx = client.set_transaction(ix, *signers) 
        response = client.send_transaction(tx).json()
        if "error" not in response:
            return json.dumps(
                {
                    'status': Status.Success,
                    'tx': tx,
                }
            )
    except:
        pass
    finally:
        return json.dumps(
            {
                'status': Status.Failure,
                'tx': tx
            }
        )