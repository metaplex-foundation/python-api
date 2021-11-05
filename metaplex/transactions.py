import json
import base64
from solana.publickey import PublicKey 
from solana.transaction import Transaction
from solana.keypair import Keypair 
from solana.rpc.api import Client
from solana.system_program import transfer, TransferParams, create_account, CreateAccountParams 
from spl.token._layouts import MINT_LAYOUT, ACCOUNT_LAYOUT
from spl.token.instructions import (
    get_associated_token_address, mint_to, MintToParams,
    transfer as spl_transfer, TransferParams as SPLTransferParams,
    burn as spl_burn, BurnParams,
    initialize_mint, InitializeMintParams,
)
from metaplex.metadata import (
    create_associated_token_account_instruction,
    create_master_edition_instruction,
    create_metadata_instruction_data, 
    create_metadata_instruction,
    get_metadata,
    update_metadata_instruction_data,
    update_metadata_instruction,
    ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
)


def deploy(api_endpoint, source_account, name, symbol, fees):
    # Initalize Client
    client = Client(api_endpoint)
    # List non-derived accounts
    mint_account = Keypair()
    token_account = TOKEN_PROGRAM_ID 
    # List signers
    signers = [source_account, mint_account]
    # Start transaction
    tx = Transaction()
    # Get the minimum rent balance for a mint account
    min_rent_reseponse = client.get_minimum_balance_for_rent_exemption(MINT_LAYOUT.sizeof()) # type: ignore
    lamports = min_rent_reseponse["result"]
    # Generate Mint 
    create_mint_account_ix = create_account(
        CreateAccountParams(
            from_pubkey=source_account.public_key,
            new_account_pubkey=mint_account.public_key,
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
            mint=mint_account.public_key,
            mint_authority=source_account.public_key,
            freeze_authority=source_account.public_key,
        )
    )
    tx = tx.add(initialize_mint_ix)
    # Create Token Metadata
    create_metadata_ix = create_metadata_instruction(
        data=create_metadata_instruction_data(name, symbol, fees, [str(source_account.public_key)]),
        update_authority=source_account.public_key,
        mint_key=mint_account.public_key,
        mint_authority_key=source_account.public_key,
        payer=source_account.public_key,
    )
    tx = tx.add(create_metadata_ix)
    return tx, signers, str(mint_account.public_key)
    

def wallet():
    """ Generate a wallet and return the address and private key. """
    account = Keypair()
    pub_key = account.public_key 
    private_key = list(account.seed)
    return json.dumps(
        {
            'address': str(pub_key),
            'private_key': private_key
        }
    )


def topup(api_endpoint, sender_account, to, amount=None):
    """
    Send a small amount of native currency to the specified wallet to handle gas fees. Return a status flag of success or fail and the native transaction data.
    """
    # Connect to the api_endpoint
    client = Client(api_endpoint)
    # List accounts 
    dest_account = PublicKey(to)
    # List signers
    signers = [sender_account]
    # Start transaction
    tx = Transaction()
    # Determine the amount to send 
    if amount is None:
        min_rent_reseponse = client.get_minimum_balance_for_rent_exemption(ACCOUNT_LAYOUT.sizeof())
        lamports = min_rent_reseponse["result"]
    else:
        lamports = int(amount)
    # Generate transaction
    transfer_ix = transfer(TransferParams(from_pubkey=sender_account.public_key, to_pubkey=dest_account, lamports=lamports))
    tx = tx.add(transfer_ix)
    return tx, signers

def update_token_metadata(api_endpoint, source_account, mint_token_id, link, data, fee, creators_addresses, creators_verified, creators_share):
    """
    Updates the json metadata for a given mint token id.
    """
    mint_account = PublicKey(mint_token_id)
    signers = [source_account]

    tx = Transaction()
    update_metadata_data = update_metadata_instruction_data(
        data['name'],
        data['symbol'],
        link,
        fee,
        creators_addresses,        
        creators_verified,
        creators_share,
    )
    update_metadata_ix = update_metadata_instruction(
        update_metadata_data,
        source_account.public_key,
        mint_account,
    )
    tx = tx.add(update_metadata_ix) 
    return tx, signers


def mint(api_endpoint, source_account, contract_key, dest_key, link, supply=1):
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
    # Initialize Client
    client = Client(api_endpoint)
    # List non-derived accounts
    mint_account = PublicKey(contract_key)
    user_account = PublicKey(dest_key)
    token_account = TOKEN_PROGRAM_ID
    # List signers
    signers = [source_account]
    # Start transaction
    tx = Transaction()
    # Create Associated Token Account
    associated_token_account = get_associated_token_address(user_account, mint_account)
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
            payer=source_account.public_key, # signer
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
            mint_authority=source_account.public_key,
            amount=1,
            signers=[source_account.public_key],
        )
    )
    tx = tx.add(mint_to_ix) 
    metadata = get_metadata(client, mint_account)
    update_metadata_data = update_metadata_instruction_data(
        metadata['data']['name'],
        metadata['data']['symbol'],
        link,
        metadata['data']['seller_fee_basis_points'],
        metadata['data']['creators'],
        metadata['data']['verified'],
        metadata['data']['share'],
    )
    update_metadata_ix = update_metadata_instruction(
        update_metadata_data,
        source_account.public_key,
        mint_account,
    )
    tx = tx.add(update_metadata_ix) 
    create_master_edition_ix = create_master_edition_instruction(
        mint=mint_account,
        update_authority=source_account.public_key,
        mint_authority=source_account.public_key,
        payer=source_account.public_key,
        supply=supply,
    )
    tx = tx.add(create_master_edition_ix) 
    return tx, signers


def send(api_endpoint, source_account, contract_key, sender_key, dest_key, private_key):
    """
    Transfer a token on a given network and contract from the sender to the recipient.
    May require a private key, if so this will be provided encrypted using Fernet: https://cryptography.io/en/latest/fernet/
    Return a status flag of success or fail and the native transaction data. 
    """
    # Initialize Client
    client = Client(api_endpoint)
    # List non-derived accounts
    owner_account = Keypair(private_key) # Owner of contract 
    sender_account = PublicKey(sender_key) # Public key of `owner_account`
    token_account = TOKEN_PROGRAM_ID
    mint_account = PublicKey(contract_key)
    dest_account = PublicKey(dest_key)
    # This is a very rare care, but in the off chance that the source wallet is the recipient of a transfer we don't need a list of 2 keys
    signers = [source_account, owner_account]
    # Start transaction
    tx = Transaction()
    # Find PDA for sender
    token_pda_address = get_associated_token_address(sender_account, mint_account)
    if client.get_account_info(token_pda_address)['result']['value'] is None: 
        raise Exception
    # Check if PDA is initialized for receiver. If not, create the account
    associated_token_account = get_associated_token_address(dest_account, mint_account)
    associated_token_account_info = client.get_account_info(associated_token_account)
    account_info = associated_token_account_info['result']['value']
    if account_info is not None: 
        account_state = ACCOUNT_LAYOUT.parse(base64.b64decode(account_info['data'][0])).state
    else:
        account_state = 0
    if account_state == 0:
        associated_token_account_ix = create_associated_token_account_instruction(
            associated_token_account=associated_token_account,
            payer=source_account.public_key, # signer
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
    return tx, signers


def burn(api_endpoint, contract_key, owner_key, private_key):
    """
    Burn a token, permanently removing it from the blockchain.
    May require a private key, if so this will be provided encrypted using Fernet: https://cryptography.io/en/latest/fernet/
    Return a status flag of success or fail and the native transaction data.
    """
    # Initialize Client
    client = Client(api_endpoint)
    # List accounts
    owner_account = PublicKey(owner_key)
    token_account = TOKEN_PROGRAM_ID
    mint_account = PublicKey(contract_key)
    # List signers
    signers = [Keypair(private_key)]
    # Start transaction
    tx = Transaction()
    # Find PDA for sender
    token_pda_address = get_associated_token_address(owner_account, mint_account)
    if client.get_account_info(token_pda_address)['result']['value'] is None: 
        raise Exception
    # Burn token
    burn_ix = spl_burn(
        BurnParams(
            program_id=token_account,
            account=token_pda_address,
            mint=mint_account,
            owner=owner_account,
            amount=1,
            signers=[],
        )
    )
    tx = tx.add(burn_ix)
    return tx, signers
