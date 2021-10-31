# Metaplex Python API

This modules allows you to create, mint, transfer and burn NFTs on the Solana blockchain using Python.

## Setup
First, clone down the repository

Create a virtual environment and install the dependencies in `requirements.txt`. Be sure to use a version of Python >= 3.6

```bash
python3 -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

At this point, you should be good to go.

## Usage

To create a `MetaplexAPI` object, you need to pass a dicitonary to the constructor with the following keys:

```python
cfg = {
    "PRIVATE_KEY": YOUR_PRIVATE_KEY,
    "PUBLIC_KEY": YOUR_PUBLIC_KEY,
    "DECRYPTION_KEY": SERVER_DECRYPTION_KEY
}
api = MetaplexAPI(cfg)
```

The keypair that is passed into the `MetaplexAPI` serves as the fee payer for all network transactions (creating new wallets, minting tokens, transferring tokens, etc). Both keys are base58 encoded.

The decryption key ensures that messages sent to a server that utilizes this API will not be receiving unencrypted private keys over the wire. These private keys are necessary for signing transactions. The client can encrypt their data by using the same decryption key as the server. This is the syntax:

```python
from cryptography.fernet import Fernet
cipher = Fernet(DECRYPTION_KEY) # This is the same key that the server has
encrypted_key = cipher.encrypt(SECRET)

# Send `encrypted_key` to the downstream server to process
```

## Methods

This section will go through the following story (if you look at the code snippets) and invoke each of the methods in the API along the way:
1) Account `A` is created and airdropped 10 SOL
2) `A` creates an NFT `N`
3) Account `B` is created
4) `A` pays `B`'s rent fee
5) `N` is minted to `B` associated token account
6) Account `C` is created
7) `A` pays `C`'s rent fee
8) `B` transfers `N` to `C`
9) `C` destroys `N` 

Let's get started:
```bash
$ python3 -i -m api.metaplex_api
>>> 
```

### deploy
`deploy` will create a new NFT token by
1) Creating a new account from a randomly generated address (invokes `CreateAccount` from the System Program)
2) Invoking `InitializeMint` on the new account
3) Initializing the metadata for this account by invoking the `CreateMetatdata` instruction from the Metaplex protocol

Args:

`api_endpoint`: (str) The RPC endpoint to connect the network. ([devnet](https://api.devnet.solana.com/), [mainnet](https://api.mainnet-beta.solana.com/))

`name`: (str) Name of the NFT Contract (32 bytes max)

`symbol`: (str) Symbol of the NFT Contract (10 bytes max)

`skip_confirmation=True`: A flag that tells you to wait for the transaction to be confirmed if set to `False` (only used for testing, because it requires synchronized/sequential calls)

Example:
```python
>>> account = KeyPair()
>>> cfg = {"PRIVATE_KEY": base58.b58encode(account.seed).decode("ascii"), "PUBLIC_KEY": str(account.public_key), "DECRYPTION_KEY": Fernet.generate_key().decode("ascii")}
>>> api_endpoint = "https://api.devnet.solana.com/"
>>> Client(api_endpoint).request_airdrop(account.public_key, int(1e10))
{'jsonrpc': '2.0', 'result': '4ojKmAAesmKtqJkNLRtEjdgg4CkmowuTAjRSpp3K36UvQQvEXwhirV85E8cvWYAD42c3UyFdCtzydMgWokH2mbM', 'id': 1}
>>> metaplex_api = MetaplexAPI(cfg)
>>> seller_basis_fees = 0 # value in 10000 
>>> metaplex_api.deploy(api_endpoint, "A"*32, "A"*10, seller_basis_fees)
'{"status": 200, "contract": "7bxe7t1aGdum8o97bkuFeeBTcbARaBn9Gbv5sBd9DZPG", "msg": "Successfully created mint 7bxe7t1aGdum8o97bkuFeeBTcbARaBn9Gbv5sBd9DZPG", "tx": "2qmiWoVi2PNeAjppe2cNbY32zZCJLXMYgdS1zRVFiKJUHE41T5b1WfaZtR2QdFJUXadrqrjbkpwRN5aG2J3KQrQx"}'
>>> 
```
Note that when sending SOL to the newly generated account, that account will serve as the fee payer. You can check out [this transaction on the Solana Block Exporer]( https://explorer.solana.com/tx/2qmiWoVi2PNeAjppe2cNbY32zZCJLXMYgdS1zRVFiKJUHE41T5b1WfaZtR2QdFJUXadrqrjbkpwRN5aG2J3KQrQx?cluster=devnet).

### wallet
`wallet` creates a new random public/private keypair

```python
>>> metaplex_api.wallet()
'{"address": "VtdBygLSt1EJF5M3nUk5CRxuNNTyZFUsKJ4yUVcC6hh", "private_key": [95, 46, 174, 145, 248, 101, 108, 111, 128, 44, 41, 212, 118, 145, 42, 242, 84, 6, 31, 115, 18, 126, 47, 230, 103, 202, 46, 7, 194, 149, 42, 213]}'
>>>
```
No network calls are made here

### topup
`topup` sends a small amount of SOL to the destination account by invoking `Transfer` from the System Program

Args:

`api_endpoint`: (str) The RPC endpoint to connect the network. ([devnet](https://api.devnet.solana.com/), [mainnet](https://api.mainnet-beta.solana.com/))

`to`: (str) The base58 encoded public key of the destination address

`amount`: (Union[int, None]) This is the number of lamports to send to the destination address. If `None` (default), then the minimum rent exemption balance is transferred.

```python
>>> metaplex_api.topup(api_endpoint, "VtdBygLSt1EJF5M3nUk5CRxuNNTyZFUsKJ4yUVcC6hh")
'{"status": 200, "msg": "Successfully sent 0.00203928 SOL to VtdBygLSt1EJF5M3nUk5CRxuNNTyZFUsKJ4yUVcC6hh", "tx": "32Dk647Fb6aKJyErVfxgtSfC4xbssoJprcB7BEmEAdYTFK96M5VEQ1z62QxCCC7tAPF1g9TNvMehoGNudLNaKTWE"}'
>>> 
```
[tx link](https://explorer.solana.com/tx/32Dk647Fb6aKJyErVfxgtSfC4xbssoJprcB7BEmEAdYTFK96M5VEQ1z62QxCCC7tAPF1g9TNvMehoGNudLNaKTWE?cluster=devnet)

### mint
`mint` will mint a token to a designated user account by
1) Fetching or creating an AssociatedTokenAccount from a Program Derived Address
2) Invoking `MintTo` with the AssociatedTokenAccount as the destination
3) Invoking the `UpdateMetadata` instruction from the Metaplex protocol to update the `uri` of the contract (containing the actual content)

Args:

`api_endpoint`: (str) The RPC endpoint to connect the network. ([devnet](https://api.devnet.solana.com/), [mainnet](https://api.mainnet-beta.solana.com/))

`contract_key`: (str) The base58 encoded public key of the mint address

`dest_key`: (str) The base58 encoded public key of the destinaion address (where the contract will be minted)

`link`: (str) The link to the content of the the NFT

```
>>> metaplex_api.mint(api_endpoint, "7bxe7t1aGdum8o97bkuFeeBTcbARaBn9Gbv5sBd9DZPG", "VtdBygLSt1EJF5M3nUk5CRxuNNTyZFUsKJ4yUVcC6hh", "https://arweave.net/1eH7bZS-6HZH4YOc8T_tGp2Rq25dlhclXJkoa6U55mM/")
'{"status": 200, "msg": "Successfully minted 1 token to DkrGGuqn183rNyYHQNo9NSDYKZB8FVsaPBGn3F6nG7iH", "tx": "5r4qY1LudNg49FXyduadoAm83cJDWVeypUX6dsGs91RJqSxzU5qTt9WXfXs3Lzs5ZGQsTDTRpDyiXorv1wCzrzsJ"}'
>>> 
```
[tx link](https://explorer.solana.com/tx/5r4qY1LudNg49FXyduadoAm83cJDWVeypUX6dsGs91RJqSxzU5qTt9WXfXs3Lzs5ZGQsTDTRpDyiXorv1wCzrzsJ?cluster=devnet)

### send
`send` will send a token from one user account to another user account
1) Fetching the AssociatedTokenAccount from a Program Derived Address for the sender
2) Fetching or creatign the AssociatedTokenAccount from a Program Derived Address for the receiver
3) Invoking `Transfer` (from the Token Program) with the receiver's AssociatedTokenAccount as the destination

Args:

`api_endpoint`: (str) The RPC endpoint to connect the network. ([devnet](https://api.devnet.solana.com/), [mainnet](https://api.mainnet-beta.solana.com/))

`contract_key`: (str) The base58 encoded public key of the mint address\

`sender_key`: (str) The base58 encoded public key of the source address (from which the contract will be transferred)

`dest_key`: (str) The base58 encoded public key of the destinaion address (to where the contract will be transferred)

`encrypted_private_key`: (bytes) The encrypted private key of the sender

```python
>>> metaplex_api.wallet()
'{"address": "EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8", "private_key": [172, 155, 209, 75, 226, 68, 91, 22, 199, 75, 148, 197, 143, 10, 211, 67, 5, 160, 101, 15, 139, 33, 208, 65, 59, 198, 5, 41, 167, 206, 85, 83]}'
>>> metaplex_api.topup(api_endpoint, "EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8")
'{"status": 200, "msg": "Successfully sent 0.00203928 SOL to EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8", "tx": "4erc1aPC8fSNV1kb41mgUSgMKMHhd8FdDd4gqFPQ9TmmS48QcaAi9zpNjzMG3UNr1dDw1mBxThZCgJyUPchiV3Jz"}'
>>> encrypted_key = metaplex_api.cipher.encrypt(bytes([95, 46, 174, 145, 248, 101, 108, 111, 128, 44, 41, 212, 118, 145, 42, 242, 84, 6, 31, 115, 18, 126, 47, 230, 103, 202, 46, 7, 194, 149, 42, 213]))
>>> metaplex_api.send(api_endpoint, "7bxe7t1aGdum8o97bkuFeeBTcbARaBn9Gbv5sBd9DZPG", "VtdBygLSt1EJF5M3nUk5CRxuNNTyZFUsKJ4yUVcC6hh", "EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8", encrypted_key)
'{"status": 200, "msg": "Successfully transfered token from VtdBygLSt1EJF5M3nUk5CRxuNNTyZFUsKJ4yUVcC6hh to EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8", "tx": "3ZsGcCfjUXviToSB4U6Wg1W1W4rm8bMT7wF8zfauTciK6PdszpLqcvmmYqqrz8mRGK8pQPABVewCk8EdsvNVhzp6"}'
```
[tx link](https://explorer.solana.com/tx/3ZsGcCfjUXviToSB4U6Wg1W1W4rm8bMT7wF8zfauTciK6PdszpLqcvmmYqqrz8mRGK8pQPABVewCk8EdsvNVhzp6?cluster=devnet)


### burn
`burn` will remove a token from the blockchain
1) Fetching the AssociatedTokenAccount from a Program Derived Address for the owner
3) Invoking `Burn` (from the Token Program) with the owner's AssociatedTokenAccount as the destination

Args:

`api_endpoint`: (str) The RPC endpoint to connect the network. (devnet: https://api.devnet.solana.com/, mainnet: https://api.mainnet-beta.solana.com/)

`contract_key`: (str) The base58 encoded public key of the mint address

`owner_key`: (str) The base58 encoded public key of the owner address

`encrypted_private_key`: (bytes) The encrypted private key of the owner

```
>>> encrypted_key = metaplex_api.cipher.encrypt(bytes([172, 155, 209, 75, 226, 68, 91, 22, 199, 75, 148, 197, 143, 10, 211, 67, 5, 160, 101, 15, 139, 33, 208, 65, 59, 198, 5, 41, 167, 206, 85, 83]))
>>> metaplex_api.burn(api_endpoint, "7bxe7t1aGdum8o97bkuFeeBTcbARaBn9Gbv5sBd9DZPG", "EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8", encrypted_key)
'{"status": 200, "msg": "Successfully burned token 7bxe7t1aGdum8o97bkuFeeBTcbARaBn9Gbv5sBd9DZPG on EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8", "tx": "5kd5g4mNBSjoTVYwAasWZx6iB8ijaELfBukKrNYBeDvLomK7iTqFH1R29yniEGcfajakDxsqmYCDgDvukihRyZeZ"}'
>>> 
```
https://explorer.solana.com/tx/5kd5g4mNBSjoTVYwAasWZx6iB8ijaELfBukKrNYBeDvLomK7iTqFH1R29yniEGcfajakDxsqmYCDgDvukihRyZeZ?cluster=devnet

### Full Example Code:

This is the sequential code from the previous section. These accounts will need to change if you want to do your own test.
```
account = KeyPair()
cfg = {"PRIVATE_KEY": base58.b58encode(account.seed).decode("ascii"), "PUBLIC_KEY": str(account.public_key), "DECRYPTION_KEY": Fernet.generate_key().decode("ascii")}
api_endpoint = "https://api.devnet.solana.com/"
Client(api_endpoint).request_airdrop(account.public_key, int(1e10))

# Create API
metaplex_api = MetaplexAPI(cfg)

# Deploy
metaplex_api.deploy(api_endpoint, "A"*32, "A"*10, 0)

# Topup VtdBygLSt1EJF5M3nUk5CRxuNNTyZFUsKJ4yUVcC6hh
metaplex_api.topup(api_endpoint, "VtdBygLSt1EJF5M3nUk5CRxuNNTyZFUsKJ4yUVcC6hh")

# Mint
metaplex_api.mint(api_endpoint, "7bxe7t1aGdum8o97bkuFeeBTcbARaBn9Gbv5sBd9DZPG", "VtdBygLSt1EJF5M3nUk5CRxuNNTyZFUsKJ4yUVcC6hh", "https://arweave.net/1eH7bZS-6HZH4YOc8T_tGp2Rq25dlhclXJkoa6U55mM/")

# Topup EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8
metaplex_api.topup(api_endpoint, "EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8")

# Send
encrypted_key = metaplex_api.cipher.encrypt(bytes([95, 46, 174, 145, 248, 101, 108, 111, 128, 44, 41, 212, 118, 145, 42, 242, 84, 6, 31, 115, 18, 126, 47, 230, 103, 202, 46, 7, 194, 149, 42, 213]))
metaplex_api.send(api_endpoint, "7bxe7t1aGdum8o97bkuFeeBTcbARaBn9Gbv5sBd9DZPG", "VtdBygLSt1EJF5M3nUk5CRxuNNTyZFUsKJ4yUVcC6hh", "EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8", encrypted_key)

# Burn
encrypted_key = metaplex_api.cipher.encrypt(bytes([172, 155, 209, 75, 226, 68, 91, 22, 199, 75, 148, 197, 143, 10, 211, 67, 5, 160, 101, 15, 139, 33, 208, 65, 59, 198, 5, 41, 167, 206, 85, 83]))
metaplex_api.burn(api_endpoint, "7bxe7t1aGdum8o97bkuFeeBTcbARaBn9Gbv5sBd9DZPG", "EnMb6ZntX43PFeX2NLcV4dtLhqsxF9hUr3tgF1Cwpwu8", encrypted_key)
 
```
