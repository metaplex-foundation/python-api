import configparser
import json
from http import HTTPStatus
from cryptography.fernet import Fernet

from solana.publickey import PublicKey 
from solana.transaction import Transaction
from solana.account import Account 
from solana.rpc.api import Client
from solana.system_program import transfer, TransferParams, create_account, CreateAccountParams 
from spl.token._layouts import MINT_LAYOUT, ACCOUNT_LAYOUT
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
)

import base64
import base58


class MetaplexAPI():

    def __init__(self, cfg):
        self.private_key = list(base58.b58decode(cfg["KEYS"]["PRIVATE_KEY"]))[:32]
        self.public_key = cfg["KEYS"]["PUBLIC_KEY"]
        self.cipher = Fernet(cfg["KEYS"]["DECRYPTION_KEY"])


    def deploy(self, network, contract, name, symbol):
        """
        Deploy a contract to the blockchain (on networks that support contracts). Takes the network ID and contract name, plus initialisers of name and symbol. Process may vary significantly between blockchains.
        Returns status code of success or fail, the contract address, and the native transaction data.
        """
        msg = ""
        try:
            # Initalize Clinet
            client = Client(network)
            # List non-derived accounts
            source_account = Account(self.private_key)
            mint_account = Account()
            token_account = TOKEN_PROGRAM_ID 
            # List signers
            signers = [source_account, mint_account]
            # Start transaction
            tx = Transaction()
            # Get the minimum rent balance for a mint account
            try:
                min_rent_reseponse = client.get_minimum_balance_for_rent_exemption(MINT_LAYOUT.sizeof())
                lamports = min_rent_reseponse["result"]
            except Exception as e:
                msg = "ERROR: Failed to receive min balance for rent exemption"
                raise(e)
            # Generate Mint 
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
            initialize_mint_ix = initialize_mint(
                InitializeMintParams(
                    decimals=0,
                    program_id=token_account,
                    mint=mint_account.public_key(),
                    mint_authority=source_account.public_key(),
                    freeze_authority=source_account.public_key(),
                )
            )
            tx = tx.add(initialize_mint_ix)
            # Create Token Metadata
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
            if "error" not in response:
                return json.dumps(
                    {
                        'status': HTTPStatus.OK,
                        'contract': str(mint_account.public_key()),
                        'msg': f"Successfully created mint {str(mint_account.public_key())}",
                        'tx': response.get('result'),
                    }
                )
            else:
                return json.dumps(
                    {
                        'status': HTTPStatus.BAD_REQUEST,
                        'response': response,
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

    def topup(self, network, to, amount=None):
        """
        Send a small amount of native currency to the specified wallet to handle gas fees. Return a status flag of success or fail and the native transaction data.
        """
        msg = ""
        try:
            # Connect to the network
            client = Client(network)
            # List accounts 
            sender_account = Account(self.private_key)
            dest_account = PublicKey(to)
            # List signers
            signers = [sender_account]
            # Start transaction
            tx = Transaction()
            # Determine the amount to send 
            try:
                if amount is None:
                    min_rent_reseponse = client.get_minimum_balance_for_rent_exemption(ACCOUNT_LAYOUT.sizeof())
                    lamports = min_rent_reseponse["result"]
                else:
                    lamports = int(amount)
            except Exception as e:
                msg = "ERROR: couldn't process lamports" 
                raise(e)
            # Generate transaction
            transfer_ix = transfer(TransferParams(from_pubkey=sender_account.public_key(), to_pubkey=dest_account, lamports=lamports))
            tx = tx.add(transfer_ix)
            # Send request
            try:
                response = client.send_transaction(tx, *signers)
            except Exception as e:
                msg = f"ERROR: Encountered exception while attempting to send transaction: {e}"
                raise(e)
            if "error" not in response:
                return json.dumps(
                    {
                        'status': HTTPStatus.OK,
                        'msg': f"Successfully sent {lamports * 1e-9} SOL to {to}",
                        'tx': response.get('result'),
                    }
                )
            else:
                return json.dumps(
                    {
                        'status': HTTPStatus.BAD_REQUEST,
                        'response': response,
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
            # Initialize Client
            client = Client(network)
            # List non-derived accounts
            source_account = Account(self.private_key)
            mint_account = PublicKey(contract)
            user_account = PublicKey(address)
            token_account = TOKEN_PROGRAM_ID
            # List signers
            signers = [source_account]
            # Start transaction
            tx = Transaction()
            # Create Associated Token Account
            associated_token_account = PublicKey.find_program_address(
                [bytes(user_account), bytes(token_account), bytes(mint_account)],
                ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
            )[0]
            associated_token_account_info = client.get_account_info(associated_token_account)
            # Check if PDA is initialized. If not, create the account
            account_info = associated_token_account_info['result']['value']
            if account_info is not None: 
                account_state = ACCOUNT_LAYOUT.parse(base64.b64decode(account_info['data'][0])).state
            else:
                account_state = 0
            if account_state == 0:
                associated_token_account_ix = create_associated_token_account_instruction(
                    associated_token_account=associated_token_account,
                    payer=source_account.public_key(), # signer
                    wallet_address=user_account,
                    token_mint_address=mint_account,
                )
                tx = tx.add(associated_token_account_ix)  
            # Mint NFT to the newly create associated token account
            mint_to_ix = mint_to(
                MintToParams(
                    program_id=TOKEN_PROGRAM_ID,
                    mint=mint_account,
                    dest=associated_token_account,
                    mint_authority=source_account.public_key(),
                    amount=1,
                    signers=[source_account.public_key()],
                )
            )
            tx = tx.add(mint_to_ix) 
            try:
                response = client.send_transaction(tx, *signers)
            except Exception as e:
                msg = f"ERROR: Encountered exception while attempting to send transaction: {e}"
                raise(e)
            if "error" not in response:
                return json.dumps(
                    {
                        'status': HTTPStatus.OK,
                        'msg': f"Successfully minted 1 token to {associated_token_account}",
                        'tx': response.get('result'),
                    }
                )
            else:
                return json.dumps(
                    {
                        'status': HTTPStatus.BAD_REQUEST,
                        'response': response,
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
            # Initialize Client
            client = Client(network)
            # Decrypt the private key
            private_key = list(self.cipher.decrypt(encrypted_private_key))
            assert(len(private_key) == 32)
            # List non-derived accounts
            source_account = Account(self.private_key)
            owner_account = Account(private_key) # Owner of contract 
            sender_account = PublicKey(sender) # Public key of `owner_account`
            token_account = TOKEN_PROGRAM_ID
            mint_account = PublicKey(contract)
            dest_account = PublicKey(to)
            # This is a very rare care, but in the off chance that the source wallet is the recipient of a transfer we don't need a list of 2 keys
            if private_key == self.private_key:
                signers = [source_account]
            else:
                signers = [source_account, owner_account]
            # Start transaction
            tx = Transaction()
            # Find PDA for sender
            token_pda_address = PublicKey.find_program_address(
                [bytes(sender_account), bytes(token_account), bytes(mint_account)],
                ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
            )[0]
            if client.get_account_info(token_pda_address)['result']['value'] is None: 
                msg = f"Associated token account for {contract} does not exist for {str(sender_account)}"
                raise Exception
            # Check if PDA is initialized for receiver. If not, create the account
            associated_token_account = PublicKey.find_program_address(
                [bytes(dest_account), bytes(token_account), bytes(mint_account)],
                ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
            )[0]
            associated_token_account_info = client.get_account_info(associated_token_account)
            account_info = associated_token_account_info['result']['value']
            if account_info is not None: 
                account_state = ACCOUNT_LAYOUT.parse(base64.b64decode(account_info['data'][0])).state
            else:
                account_state = 0
            if account_state == 0:
                associated_token_account_ix = create_associated_token_account_instruction(
                    associated_token_account=associated_token_account,
                    payer=source_account.public_key(), # signer
                    wallet_address=dest_account,
                    token_mint_address=mint_account,
                )
                tx = tx.add(associated_token_account_ix)        
            # Transfer the Token from the sender account to the associated token account
            spl_transfer_ix = spl_transfer(
                SPLTransferParams(
                    program_id=token_account,
                    source=token_pda_address,
                    dest=associated_token_account,
                    owner=sender_account,
                    signers=[],
                    amount=1,
                )
            )
            tx = tx.add(spl_transfer_ix)
            # Send request
            try:
                response = client.send_transaction(tx, *signers)
            except Exception as e:
                msg = f"ERROR: Encountered exception while attempting to send transaction: {e}"
                raise(e)
            if "error" not in response:
                return json.dumps(
                    {
                        'status': HTTPStatus.OK,
                        'msg': f"Successfully transfered token from {sender} to {to}",
                        'tx': response.get('result'),
                    }
                )
            else:
                return json.dumps(
                    {
                        'status': HTTPStatus.BAD_REQUEST,
                        'response': response,
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
            # Initialize Client
            client = Client(network)
            # Decrypt the private key
            private_key = list(self.cipher.decrypt(encrypted_private_key))
            assert(len(private_key) == 32)
            # List accounts
            owner_account = Account(private_key) # Owner of contract 
            sender_account = PublicKey(sender) # Public key of `owner_account` 
            token_account = TOKEN_PROGRAM_ID
            mint_account = PublicKey(contract)
            # List signers
            signers = [owner_account]
            # Start transaction
            tx = Transaction()
            # Find PDA for sender
            token_pda_address = PublicKey.find_program_address(
                [bytes(sender_account), bytes(token_account), bytes(mint_account)],
                ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
            )[0]
            if client.get_account_info(token_pda_address)['result']['value'] is None: 
                msg = f"Associated token account for {contract} does not exist for {str(sender_account)}"
                raise Exception
            # Burn token
            burn_ix = burn(
                BurnParams(
                    program_id=token_account,
                    account=token_pda_address,
                    mint=mint_account,
                    owner=sender_account,
                    amount=1,
                    signers=[],
                )
            )
            tx = tx.add(burn_ix)
            # Send request
            try:
                response = client.send_transaction(tx, *signers)
            except Exception as e:
                msg = f"ERROR: Encountered exception while attempting to send transaction: {e}"
                raise(e)
            if "error" not in response:
                return json.dumps(
                    {
                        'status': HTTPStatus.OK,
                        'msg': f"Successfully burned token {str(mint_account)} on {str(sender_account)}",
                        'tx': response.get('result'),
                    }
                )
            else:
                return json.dumps(
                    {
                        'status': HTTPStatus.BAD_REQUEST,
                        'response': response,
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