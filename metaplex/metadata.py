from enum import IntEnum
from construct import (
    BitStruct, BitsInteger, BitsSwapped, Bytes, Const, Flag, Int8ul, Int16ul, Int32ul, Int64ul, Padding, Switch
)
from construct import Struct as cStruct  # type: ignore
from solana.publickey import PublicKey
from solana.transaction import AccountMeta, TransactionInstruction
from collections import namedtuple

MAX_NAME_LENGTH = 32
MAX_SYMBOL_LENGTH = 10
MAX_URI_LENGTH = 200
MAX_CREATOR_LENGTH = 34
MAX_CREATOR_LIMIT = 5
class InstructionType(IntEnum):
    """Token instruction types."""
    CREATE_METADATA = 0

DATA = cStruct(
    "name" / Bytes(MAX_NAME_LENGTH),
    "symbol" / Bytes(MAX_SYMBOL_LENGTH) ,
    "uri" / Bytes(MAX_URI_LENGTH),
    "seller_fee_basis_points" / Int16ul,
    "creators" / Bytes(MAX_CREATOR_LENGTH * MAX_CREATOR_LIMIT),
)

CREATE_METADATA_ARGS_LAYOUT = cStruct(
    "data" / DATA,
    "is_mutable" / Flag,
)

CREATE_METADATA_LAYOUT = cStruct(
    "create_metadata_args" / CREATE_METADATA_ARGS_LAYOUT,
)

INSTRUCTIONS_LAYOUT = cStruct(
    "instruction_type" / Int8ul,
    "args"
    / Switch(
        lambda this: this.instruction_type,
        {
            InstructionType.CREATE_METADATA: CREATE_METADATA_LAYOUT,
        },
    ),
)

METADATA_PROGRAM_ID = PublicKey('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s')
SYSTEM_PROGRAM_ID = PublicKey('11111111111111111111111111111111')
SYSVAR_RENT_PUBKEY = PublicKey('SysvarRent111111111111111111111111111111111') 
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID = PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
TOKEN_PROGRAM_ID = PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')

def create_associated_token_account_instruction(assosiated_token_account, payer, wallet_address, token_mint_address):
    keys = [
        AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
        AccountMeta(pubkey=assosiated_token_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=wallet_address, is_signer=False, is_writable=False),
        AccountMeta(pubkey=token_mint_address, is_signer=False, is_writable=False),
        AccountMeta(pubkey=SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False),
    ]
    return TransactionInstruction(keys=keys, program_id=ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID, data=b'')


def create_metadata_instruction_data(name, symbol, uri, seller_fee_basis_points, creators):
    _data = dict(
        name=name,
        symbol=symbol,
        uri=uri,
        seller_fee_basis_points=seller_fee_basis_points,
        creators=creators
    )
    _create_metadata_args = dict(create_metadata_args=dict(args=dict(data=_data, is_mutable=True)))
    return INSTRUCTIONS_LAYOUT.build(
        dict(
            instruction_type=InstructionType.CREATE_METADATA,
            args=_create_metadata_args,
        )
    )

def create_metadata_instruction(data, update_authority, mint_key, mint_authority_key, payer):
    metadata_account = PublicKey.find_program_address(
        [b'metadata', bytes(METADATA_PROGRAM_ID), bytes(mint_key)],
        METADATA_PROGRAM_ID
    )
    keys = [
        AccountMeta(pubkey=metadata_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=mint_key, is_signer=False, is_writable=False),
        AccountMeta(pubkey=mint_authority_key, is_signer=True, is_writable=False),
        AccountMeta(pubkey=payer, is_signer=True, is_writable=False),
        AccountMeta(pubkey=update_authority, is_signer=False, is_writable=False),
        AccountMeta(pubkey=SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False),
    ]
    return TransactionInstruction(keys=keys, program_id=METADATA_PROGRAM_ID, data=data)