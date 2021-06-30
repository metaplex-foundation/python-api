from itertools import chain
import struct
from enum import IntEnum
from construct import (
    BitStruct, BitsInteger, BitsSwapped, Bytes, Const, Flag, Int8ul, Int16ul, Int32ul, Int64ul, Padding, Switch
)
from construct import Struct as cStruct  # type: ignore
from solana.publickey import PublicKey
from solana.transaction import AccountMeta, TransactionInstruction
from collections import namedtuple
import base58

MAX_NAME_LENGTH = 32
MAX_SYMBOL_LENGTH = 10
MAX_URI_LENGTH = 200
MAX_CREATOR_LENGTH = 34
MAX_CREATOR_LIMIT = 5
class InstructionType(IntEnum):
    """Token instruction types."""
    CREATE_METADATA = 0

METADATA_PROGRAM_ID = PublicKey('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s')
SYSTEM_PROGRAM_ID = PublicKey('11111111111111111111111111111111')
SYSVAR_RENT_PUBKEY = PublicKey('SysvarRent111111111111111111111111111111111') 
ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID = PublicKey('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
TOKEN_PROGRAM_ID = PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')

def create_associated_token_account_instruction(associated_token_account, payer, wallet_address, token_mint_address):
    keys = [
        AccountMeta(pubkey=payer, is_signer=True, is_writable=True),
        AccountMeta(pubkey=associated_token_account, is_signer=False, is_writable=True),
        AccountMeta(pubkey=wallet_address, is_signer=False, is_writable=False),
        AccountMeta(pubkey=token_mint_address, is_signer=False, is_writable=False),
        AccountMeta(pubkey=SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=SYSVAR_RENT_PUBKEY, is_signer=False, is_writable=False),
    ]
    return TransactionInstruction(keys=keys, program_id=ASSOCIATED_TOKEN_ACCOUNT_PROGRAM_ID)

def _get_data_buffer(name, symbol, uri, creators):
    args =  [
        len(name),
        *list(name.encode()),
        len(symbol),
        *list(symbol.encode()),
        len(uri),
        *list(uri.encode()),
        0,
    ]
    byte_fmt = "<" 
    byte_fmt += "I" + "B"*len(name)
    byte_fmt += "I" + "B"*len(symbol)
    byte_fmt += "I" + "B"*len(uri)
    byte_fmt += "h"
    byte_fmt += "B"
    if creators:
        args.append(1)
        byte_fmt += "I"
        args.append(len(creators))
        for creator in creators: 
            byte_fmt +=  "B"*32 + "B" + "B"
            args.extend(list(base58.b58decode(creator)))
            args.append(1) # verified = True
            args.append(100) # share = 100
    else:
        args.append(0) 
    buffer = struct.pack(byte_fmt, *args)
    return buffer
    
def create_metadata_instruction_data(name, symbol, creators):
    _data = _get_data_buffer(name, symbol, " "*64, creators)
    metadata_args_layout = cStruct(
        "data" / Bytes(len(_data)),
        "is_mutable" / Flag,
    )
    _create_metadata_args = dict(data=_data, is_mutable=True)
    instruction_layout = cStruct(
        "instruction_type" / Int8ul,
        "args" / metadata_args_layout,
    )
    return instruction_layout.build(
        dict(
            instruction_type=InstructionType.CREATE_METADATA,
            args=_create_metadata_args,
        )
    )

def create_metadata_instruction(data, update_authority, mint_key, mint_authority_key, payer):
    metadata_account = PublicKey.find_program_address(
        [b'metadata', bytes(METADATA_PROGRAM_ID), bytes(PublicKey(mint_key))],
        METADATA_PROGRAM_ID
    )[0]
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