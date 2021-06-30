from construct import (
    BitStruct, BitsInteger, BitsSwapped, Bytes, Const, Flag, Int8ul, Int16ul, Int32ul, Int64ul, Padding, Switch
)
from construct import Struct as cStruct  # type: ignore
import solana.publickey import PublicKey
from solana.transaction import AccountMeta, TransactionInstruction
from collections import namedtuple

class InstructionType(IntEnum):
    """Token instruction types."""
    CREATE_METADATA = 0


DATA = cStruct(
    "name" / Bytes(32),
    "symbol" / Bytes(10) ,
    "uri" / Bytes(200),
    "seller_fee_basis_points" / Int16ul,
    "creators" / Bytes(170),
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

CREATE_METADATA_LAYOUT = cStruct(
    "create_metadta_args" / CREATE_METADATA_ARGS_LAYOUT,
)

CREATE_METADATA_ARGS_LAYOUT = cStruct(
    "data" / DATA,
    "is_mutable" / Flag,
)


METADATA_PROGRAM_ID = "TODO"
SYSTEM_PROGRAM_ID = "TODO"
SYSVAR_RENT_PUBKEY = "TODO"


def create_metadata(data, update_authority, mint_key, mint_authority_key, instructions, payer):
    metadata_account = PublicKey.find_program_address(b'metadata', METADATA_PROGRAM_ID)
    _create_metadata_args = CREATE_METADATA_ARGS_LAYOUT.build(dict(data=data, is_mutable=True))
    payload = INSTRUCTIONS_LAYOUT.build(
        dict(
            instruction_type=InstructionType.CREATE_METADATA,
            args=dict(create_metadata_args=_create_metadata_args)
        )
    )
    keys = [
        AccountMeta(
            pubkey=metadata_account,
            is_signer=False,
            is_writable=True,
        ),
        AccountMeta(
            pubkey=mint_key,
            is_signer=False,
            is_writable=False,
        ),
        AccountMeta(
            pubkey=mint_authority_key,
            is_signer=True,
            is_writable=False,
        ),
        AccountMeta(
            pubkey=payer,
            is_signer=True,
            is_writable=False,
        ),
        AccountMeta(
            pubkey=update_authority,
            is_signer=False,
            is_writable=False,
        ),
        AccountMeta(
            pubkey=SYSTEM_PROGRAM_ID,
            is_signer=False,
            is_writable=False,
        ),
        AccountMeta(
            pubkey=SYSVAR_RENT_PUBKEY,
            is_signer=False,
            is_writable=False,
        ),
    ]
    return TransactionInstruction(keys=keys, program_id=METADATA_PROGRAM_ID, data=payload)