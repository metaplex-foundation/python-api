import configparser
import json
from http import HTTPStatus
from cryptography.fernet import Fernet

from solana.publickey import PublicKey 
from solana.transaction import Transaction
from solana.account import Account 
from solana.rpc.api import Client
from solana.system_program import transfer, TransferParams 
from spl.token.instructions import (
    mint_to, MintToParams, transfer as spl_transfer, burn, BurnParams
)
import base58
class MetaplexAPI():

    def __init__(self, cfg):
        self.private_key = list(base58.b58decode(cfg["KEYS"]["PRIVATE_KEY"]))[:32]
        self.public_key = cfg["KEYS"]["PUBLIC_KEY"]
        self.token_program_id = cfg["KEYS"]["TOKEN_PROGRAM_ID"]
        self.cipher = Fernet(cfg["KEYS"]["DECRYTPTION_KEY"])

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

    def wallet(self):
        """ Generate a wallet on the specified network and return the address and private key. """
        account = Account()
        pub_key = account.public_key() 
        private_key = list(account.secret_key()[:32])
        return json.dumps(
            {
                'address': str(pub_key),
                'private_key': private_key
            }
        )

    def topup(self, network, to, amount):
        """
        Send a small amount of native currency to the specified wallet to handle gas fees. Return a status flag of success or fail and the native transaction data.
        """
        msg = ""
        try:
            # Connect to the network
            client = Client(network)
            # Get the sender account
            try:
                sender = Account(self.private_key)
            except Exception as e:
                msg = "ERROR: Invalid private key"
                raise(e)
            signers = [sender]
            # Validate amount 
            try:
                lamports = int(amount)
            except Exception as e:
                msg = "ERROR: `amount` must be an int"
                raise(e)
            # Generate transaction
            ix = transfer(TransferParams(from_pubkey=sender.public_key(), to_pubkey=PublicKey(to), lamports=lamports))
            tx = Transaction().add(ix)
            # Send request
            try:
                response = client.send_transaction(tx, *signers)
            except Exception as e:
                msg = f"ERROR: Encountered exception while attempting to send transaction: {e}"
                raise(e)
            # Pull byte array from initial transaction
            tx_payload = list(tx.serialize())

            if "error" not in response:
                return json.dumps(
                    {
                        'status': HTTPStatus.OK,
                        'msg': f"Successfully sent {amount * 1e-9} SOL to {to}",
                        'tx': tx_payload,
                        'response': response.get('result'),
                    }
                )
            else:
                return json.dumps(
                    {
                        'status': HTTPStatus.BAD_REQUEST,
                        'response': response,
                        'tx': tx_payload,
                    }
                )
        except Exception as e:
            return json.dumps(
                {
                    'status': HTTPStatus.BAD_REQUEST,
                    'msg': msg,
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
        msg = ""
        try:
            client = Client(network)
            signers = [Account(self.private_key)]
            mint_to_params = MintToParams(
                program_id=PublicKey(self.token_program_id),
                mint=PublicKey(contract),
                dest=PublicKey(address),
                mint_authority=PublicKey(self.public_key),
                amount=1,
                signers=signers,
            )
            ix = mint_to(mint_to_params)
            tx = Transaction().add(ix) 
            try:
                response = client.send_transaction(tx, *signers)
            except Exception as e:
                msg = f"ERROR: Encountered exception while attempting to send transaction: {e}"
                raise(e)
            tx_payload = list(tx.serialize())
            if "error" not in response:
                return json.dumps(
                    {
                        'status': HTTPStatus.OK,
                        'msg': f"Successfully minted 1 token to {address}",
                        'response': response.get('result'),
                        'tx': tx_payload,
                    }
                )
            else:
                return json.dumps(
                    {
                        'status': HTTPStatus.BAD_REQUEST,
                        'response': response,
                        'tx': tx_payload,
                    }
                )
        except:
            return json.dumps(
                {
                    'status': HTTPStatus.BAD_REQUEST,
                    'msg': msg,
                }
            )

    def send(self, network, contract, sender, to, token, encrypted_private_key, contract_address):
        """
        Transfer a token on a given network and contract from the sender to the recipient.
        May require a private key, if so this will be provided encrypted using Fernet: https://cryptography.io/en/latest/fernet/
        Return a status flag of success or fail and the native transaction data. 
        """
        msg = ""
        try:
            client = Client(network)
            private_key = self.cipher.decrypt(encrypted_private_key).decode('utf-8')
            signers = [Account(self.private_key), Account(private_key)]
            spl_transfer_params = TransferParams(
                program_id=PublicKey(self.token_account),
                source=PublicKey(sender),
                dest=PublicKey(to),
                owner=PublicKey(contract_address),
                signers=signers,
                amount=1,
            )
            ix = spl_transfer(spl_transfer_params)
            tx = Transaction().add(ix)
            # Send request
            try:
                response = client.send_transaction(tx, *signers)
            except Exception as e:
                msg = f"ERROR: Encountered exception while attempting to send transaction: {e}"
                raise(e)
            # Pull byte array from initial transaction
            tx_payload = list(tx.serialize())
            if "error" not in response:
                return json.dumps(
                    {
                        'status': HTTPStatus.OK,
                        'msg': f"Successfully transfered token from {sender} to {to}",
                        'tx': tx_payload,
                        'response': response.get('result'),
                    }
                )
            else:
                return json.dumps(
                    {
                        'status': HTTPStatus.BAD_REQUEST,
                        'response': response,
                        'payload': tx_payload,
                    }
                )
        except Exception as e:
            return json.dumps(
                {
                    'status': HTTPStatus.BAD_REQUEST,
                    'msg': msg,
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
                        'status': HTTPStatus.OK,
                        'tx': tx,
                    }
                )
        except:
            pass
        finally:
            return json.dumps(
                {
                    'status': HTTPStatus.BAD_REQUEST,
                    'tx': tx
                }
            )