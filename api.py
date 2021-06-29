from enum import Enum
import json
from solana.publickey import PublicKey 
from solana.transaction import Transaction
from solana.account import Account 
from solana.rpc.api import Client
from solana.system_program import transfer, TransferParams 
from spl.token.instructions import (
    mint_to, MintToParams, transfer as spl_transfer, burn, BurnParams
)
import base58
from nacl.public import PrivateKey
from nacl import signing
import cherrypy

Status = Enum("Success", "Failure")

class MetaplexAPI():

    def __init__(self, cfg):
        self.private_key = cfg["PRIVATE_KEY"]
        self.public_key = cfg["PUBLIC_KEY"]
        self.token_account = cfg["TOKEN_ACCOUNT_KEY"]

    @cherrypy.expose
    def index(self):
        return "Hello World!"

    @cherrypy.expose
    def deploy(self, network, contract, name, symbol):
        """
        Deploy a contract to the blockchain (on networks that support contracts). Takes the network ID and contract name, plus initialisers of name and symbol. Process may vary significantly between blockchains.
        Returns status code of success or fail, the contract address, and the native transaction data.
        """
        status = None
        address = None
        tx = None
        # TODO
        return json.dumps(
            {
                'status': status,
                'address': address,
                'tx': tx,
            }
        )

    @cherrypy.expose
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

    @cherrypy.expose
    def topup(self, network, to, amount):
        """
        Send a small amount of native currency to the specified wallet to handle gas fees. Return a status flag of success or fail and the native transaction data.
        """
        try:
            client = Client(network)
            sender = Account(self.private_key)
            signers = [sender]
            ix = transfer(TransferParams(from_pubkey=sender.public_key(), to_pubkey=PublicKey(to), lamports=amount))
            tx = Transaction().add(ix)
            response = client.send_transaction(tx, *signers).json()
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

    @cherrypy.expose
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
            client = Client(network)
            signers = [Account(self.private_key)]
            mint_to_params = MintToParams(
                program_id=PublicKey(self.token_account),
                mint=PublicKey(contract), # Is this the one?
                dest=PublicKey(address),
                owner=PublicKey(self.public_key),
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

    @cherrypy.expose
    def send(self, network, contract, sender, to, token, private_key, contract_address):
        """
        Transfer a token on a given network and contract from the sender to the recipient.
        May require a private key, if so this will be provided encrypted using Fernet: https://cryptography.io/en/latest/fernet/
        Return a status flag of success or fail and the native transaction data. 
        """
        tx = None
        try:
            client = Client(network)
            signers = [Account(self.private_key), Account(private_key)]
            spl_transfer_params = TransferParams(
                program_id=PublicKey(self.token_account),
                source=PublicKey(sender),
                dest=PublicKey(to),
                owner=PublicKey(self.public_key),
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

    @cherrypy.expose
    def burn(self, network, contract, sender, token, private_key, contract_address):
        """
        Burn a token, permanently removing it from the blockchain.
        May require a private key, if so this will be provided encrypted using Fernet: https://cryptography.io/en/latest/fernet/
        Return a status flag of success or fail and the native transaction data.
        """
        tx = None
        try:
            client = Client(network)
            signers = [Account(self.SOURCE_ACCOUNT_KEY), Account(private_key)]
            burn_params = BurnParams(
                program_id=PublicKey(self.TOKEN_PROGRAM_ID),
                account=PublicKey(sender),
                mint=PublicKey(self.MINT_ACCOUNT_KEY),
                owner=PublicKey(self.SOURCE_ACCOUNT_PUBKEY),
                amount=1,
                signers=signers,
            )
            ix = burn(burn_params)
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

cherrypy.quickstart(MetaplexAPI())