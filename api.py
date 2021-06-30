import configparser
import json
from http import HTTPStatus
from cryptography.fernet import Fernet

from solana.publickey import PublicKey 
from solana.blockhash import Blockhash
from solana.rpc.commitment import Commitment, Max
import solana.rpc.types as types
from solana.transaction import Transaction
from solana.account import Account 
from solana.rpc.api import Client
from solana.system_program import transfer, TransferParams, create_account, CreateAccountParams 
from spl.token._layouts import MINT_LAYOUT
from spl.token.instructions import (
    mint_to, MintToParams,
    transfer as spl_transfer, TransferParams as SPLTransferParams,
    burn, BurnParams,
    initialize_mint, InitializeMintParams,
)

from metaplex.metadata import (
    create_associated_token_account_instruction,
    create_metadata_instruction_data, 
    create_metadata_instruction,
    ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    MAX_NAME_LENGTH,
    MAX_SYMBOL_LENGTH,
    MAX_URI_LENGTH,
    MAX_CREATOR_LENGTH,
    MAX_CREATOR_LIMIT,
)

import base58


class MetaplexAPI():

    def __init__(self, cfg):
        self.private_key = list(base58.b58decode(cfg["KEYS"]["PRIVATE_KEY"]))[:32]
        self.public_key = cfg["KEYS"]["PUBLIC_KEY"]
        self.cipher = Fernet(cfg["KEYS"]["DECRYPTION_KEY"])

    def create_mint(self, network):
        msg = ""
        try:
            # Create a new keypair
            mint_account = Account()

            client = Client(network)
            tx = Transaction()
            try:
                sender = Account(self.private_key)
            except Exception as e:
                msg = "ERROR: Invalid private key"
                raise(e)
            signers = [sender, mint_account] 
            # Validate amount 
            try:
                min_rent_reseponse = client.get_minimum_balance_for_rent_exemption(MINT_LAYOUT.sizeof())
                lamports = min_rent_reseponse["result"]
            except Exception as e:
                msg = "ERROR: `amount` must be an int"
                raise(e)

            # Generate transaction
            ix = create_account(
                CreateAccountParams(
                    from_pubkey=sender.public_key(),
                    new_account_pubkey=mint_account.public_key(),
                    lamports=lamports,
                    space=MINT_LAYOUT.sizeof(),
                    program_id=TOKEN_PROGRAM_ID,
                )
            )
            tx = tx.add(ix)
            initialize_mint_params = InitializeMintParams(
                decimals=0,
                program_id=TOKEN_PROGRAM_ID,
                mint=mint_account.public_key(),
                mint_authority=sender.public_key(),
                freeze_authority=sender.public_key(),
            )
            initialize_mint_ix = initialize_mint(initialize_mint_params)

            tx = tx.add(initialize_mint_ix)
            try:
                import pdb; pdb.set_trace()
                blockhash_resp = client._provider.make_request(types.RPCMethod("getRecentBlockhash"), {client._comm_key: Max})
                if not blockhash_resp["result"]:
                    raise RuntimeError("failed to get recent blockhash")
                tx.recent_blockhash = Blockhash(blockhash_resp["result"]["value"]["blockhash"])
                tx.sign(*signers)
                response = client.send_raw_transaction(tx.serialize(), opts=types.TxOpts())
            except Exception as err:
                raise RuntimeError("failed to get recent blockhash") from err

                # msg = f"ERROR: Encountered exception while attempting to send transaction: {e}"
                # raise(e)
            # Pull byte array from initial transaction
            tx_payload = list(tx.serialize())
            if "error" not in response:
                return json.dumps(
                    {
                        'status': HTTPStatus.OK,
                        'contract': str(mint_account.public_key()),
                        'msg': f"Successfully minted {str(mint_account.public_key())}",
                        'tx': tx_payload,
                        'response': response.get('result'),
                    }
                )
            else:
                return json.dumps(
                    {
                        'status': HTTPStatus.BAD_REQUEST,
                        'contract': str(mint_account.public_key()),
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
         
    
    def deploy(self, network, contract, name, symbol):
        """
        Deploy a contract to the blockchain (on networks that support contracts). Takes the network ID and contract name, plus initialisers of name and symbol. Process may vary significantly between blockchains.
        Returns status code of success or fail, the contract address, and the native transaction data.
        """
        msg = ""
        try:
            client = Client(network)
            tx = Transaction()
            source_account = Account(self.private_key)
            mint_account = Account()
            token_account = PublicKey(contract)

            signers = [source_account, mint_account]


            try:
                min_rent_reseponse = client.get_minimum_balance_for_rent_exemption(MINT_LAYOUT.sizeof())
                lamports = min_rent_reseponse["result"]
            except Exception as e:
                msg = "ERROR: `amount` must be an int"
                raise(e)

            # Generate transaction
            create_mint_account_ix = create_account(
                CreateAccountParams(
                    from_pubkey=source_account.public_key(),
                    new_account_pubkey=mint_account.public_key(),
                    lamports=lamports,
                    space=MINT_LAYOUT.sizeof(),
                    program_id=token_account,
                )
            )
            tx = tx.add(create_mint_account_ix)
            initialize_mint_params = InitializeMintParams(
                decimals=0,
                program_id=token_account,
                mint=mint_account.public_key(),
                mint_authority=source_account.public_key(),
                freeze_authority=source_account.public_key(),
            )
            initialize_mint_ix = initialize_mint(initialize_mint_params)
            tx = tx.add(initialize_mint_ix)

            recipient_key = PublicKey.find_program_address(
                [bytes(source_account.public_key()), bytes(contract), bytes(mint_account.public_key())],
                ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
            )[0]
            associated_token_account_ix = create_associated_token_account_instruction(
                associated_token_account=recipient_key,
                payer=source_account.public_key(),
                wallet_address=source_account.public_key(),
                token_mint_address=mint_account.public_key(),
            )
            tx = tx.add(associated_token_account_ix)        

            create_metadata_ix = create_metadata_instruction(
                data=create_metadata_instruction_data(name, symbol, [str(source_account.public_key())]),
                update_authority=source_account.public_key(),
                mint_key=mint_account.public_key(),
                mint_authority_key=source_account.public_key(),
                payer=source_account.public_key(),
            )
            tx = tx.add(create_metadata_ix)

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
                        'contract': str(mint_account.public_key()),
                        'msg': f"Successfully minted {str(mint_account.public_key())}",
                        'tx': tx_payload,
                        'response': response.get('result'),
                    }
                )
            else:
                return json.dumps(
                    {
                        'status': HTTPStatus.BAD_REQUEST,
                        'contract': str(mint_account.public_key()),
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
                program_id=TOKEN_PROGRAM_ID,
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
            private_key = self.cipher.decrypt(encrypted_private_key).decode('ascii')
            signers = [Account(self.private_key), Account(private_key)]
            # TODO: Verify these params
            spl_transfer_params = SPLTransferParams(
                program_id=TOKEN_PROGRAM_ID,
                source=PublicKey(sender),
                dest=PublicKey(to),
                owner=PublicKey(self.public_key),
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
                        'msg': f"Successfully burned token",
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

    def burn(self, network, contract, sender, token, encrypted_private_key, contract_address):
        """
        Burn a token, permanently removing it from the blockchain.
        May require a private key, if so this will be provided encrypted using Fernet: https://cryptography.io/en/latest/fernet/
        Return a status flag of success or fail and the native transaction data.
        """
        msg = ""
        try:
            client = Client(network)
            private_key = self.cipher.decrypt(encrypted_private_key).decode('ascii')
            signers = [Account(self.private_key) ,Account(private_key)]
            # TODO: Verify these params
            burn_params = BurnParams(
                program_id=TOKEN_PROGRAM_ID,
                account=PublicKey(sender),
                mint=PublicKey(contract_address),
                owner=PublicKey(self.public_key),
                amount=1,
                signers=signers,
            )
            ix = burn(burn_params)
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
                        'msg': f"Successfully burned token",
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

if __name__ == "__main__":
    cfg = configparser.ConfigParser()
    cfg.read("config.ini")
    api = MetaplexAPI(cfg)