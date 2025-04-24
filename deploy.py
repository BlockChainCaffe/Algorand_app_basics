#!/usr/bin/python3

import shelve
import timeit
import json
from pathlib import Path
from base64 import b64decode

from algokit_utils import SigningAccount
from algosdk.transaction import ApplicationCreateTxn, StateSchema, OnComplete, wait_for_confirmation, PaymentTxn
from algosdk.logic import get_application_address
from algosdk.v2client.algod import AlgodClient


'''
----------------------------------------------------------------------------------------------------    
    PART1: get all data & info needed to deploy the contract
----------------------------------------------------------------------------------------------------    
'''

## Globals
private_key             = None
address                 = None
algod_address           = None
algod_token             = None
teal_approval_file      = None
teal_clear_file         = None
contract_name           = None
lora_link               = None
app_id                  = None
application_address     = None
signer                  = None

global_num_uints        = 0
global_num_byte_slices  = 0
local_num_uints         = 0
local_num_byte_slices   = 0

## 100_000 for the creator MBR,
# 100_000 to fund the application address MBR, 2_000 for the 2 transactions
required_balance        = 202_000


## Check if an address is already there
with shelve.open("shelve.db") as db:
    if 'private_key' in db and 'address' in db:
        private_key = db['private_key']
        address = db['address']
        print("🟢 Using private key: ", private_key)
        print("🟢 Using address: ", address)
    else:
        print("❌ No account found in shelve.db. Create one first")
        exit(1001)

    if 'algod_address' in db:
        algod_address = db['algod_address']
        print("🟢 Using net: ", algod_address)
    else:
        print("❌ Algorand client address not specified")
        exit(1002)

    if 'algod_token' in db:
        algod_token = db['algod_token']
        print("🟢 Using token: ", algod_token)
    else:
        print("❌ Algorand token address not specified")
        exit(1002)
    if 'lora_link' in db:
        lora_link = db['lora_link']

## Check that account is correct
signer = SigningAccount(private_key=private_key)
if address != signer.address:
    print("❌ Private key and address dont' match")
    exit(1003)


'''
----------------------------------------------------------------------------------------------------    
    PART2: Connect to the network
----------------------------------------------------------------------------------------------------    
'''

## Connect to Algorand network/node via algod_client
try:
    algod_client = AlgodClient(
        algod_address= algod_address,
        algod_token= algod_token
    )
    status = algod_client.status()
    if 'last-round' in status:
        print("✅ Connected")
        print("🕓 Last round: ", status['last-round'])
except Exception as e:
    print("💩 ", e)
    print("❌ Could not connet! Quitting")
    exit(1005)

## Get some account info (it's a check that we can speak to the node)
try:
    account_info = algod_client.account_info(address)
    print("💰 Account balance", account_info['amount']/1_000_000, "algos")
    print("🏦 Minimum balance", account_info['min-balance']/1_000_000, "algos")
except Exception as e:
    print("💩 ", e)
    print("❌ Could not get address info! Quitting")
    exit(1006)
if  (account_info['amount'] - account_info['min-balance'])< required_balance:
    print("💸 You are too poor! Quitting")
    exit(1007)



'''
----------------------------------------------------------------------------------------------------    
    PART3: Compile the contract for deploy
----------------------------------------------------------------------------------------------------    
'''
## Get teal files
try:
    directory = Path('./')
    teal_files = list(directory.glob('*.teal'))                                         ## search for *teal files
    teal_files = list(map(lambda x: str(x), teal_files))                                ## turn them into strings
    ## Check we have exactly 2 files for 1 contract
    if len(teal_files) != 2:
        print("❌ Too many contracts ! Quitting")
        exit(1008)
    teal_approval_file = list(filter(lambda f: '.approval.teal' in f , teal_files))[0]  ## extract the approval file name
    teal_clear_file = list(filter(lambda f: '.clear.teal' in f , teal_files))[0]        ## extract the clear file name
    ## Check both files refer to same contract
    contract_name_1 = teal_approval_file.replace(".approval.teal", "")
    contract_name_2 = teal_clear_file.replace(".clear.teal", "")
    if contract_name_1 == contract_name_2:
        contract_name = contract_name_1
    else:
        print("❌ Mess in teal files ! Quitting")
        exit(1009)
    print("✅ Got teal files")
except Exception as e:
    print("💩 ", e)
    print("❌ Could not find teal files ! Quitting")
    exit(1010)

## Compile teal files
try:
    start_time = timeit.default_timer()
    with open(f'./{teal_approval_file}' ,'r') as f:
        approval_teal_source=f.read()
    with open(f'./{teal_clear_file}' ,'r') as f:
        clear_teal_source=f.read()
    approval_program = b64decode((algod_client.compile(approval_teal_source))['result'])
    clear_program = b64decode((algod_client.compile(clear_teal_source))['result'])
    elapsed = timeit.default_timer() - start_time
    print(f"✅ Compiled teal files ({elapsed})")
except Exception as e:
    print("❌ ", e)
    print("❌ Could not compile teal files ! Quitting")
    exit(1011)



'''
----------------------------------------------------------------------------------------------------    
    PART4: Deploy the compiled contract
----------------------------------------------------------------------------------------------------    
'''

## Get extended abi file
try:
    directory = Path('./')
    abi_file = list(directory.glob('*.arc56.json'))
    abi_file = list(map(lambda x: str(x), abi_file))
    if len(abi_file) != 1:
        print("❌ Exaclty 1 ABI file expected ! Quitting")
        exit(2009)
    else:
        abi_file = abi_file[0]
        with open(f'./'+abi_file ,'r') as f:
            abi=json.loads(f.read())
        print("🟢 Read ABI file")
except Exception as e:
    print("💩 ", e)
    print("❌ Error reading ABI file! Quitting")
    exit(2010)

## Get storage allocation values (if any) from ABI
try:
    global_num_uints        = abi['state']['schema']['global']['ints']
    global_num_byte_slices  = abi['state']['schema']['global']['bytes']
    local_num_uints         = abi['state']['schema']['local']['ints']
    local_num_byte_slices   = abi['state']['schema']['local']['bytes']
except Exception as e:
    print("💩 ", e)
    print("❌ Error reading ABI data! Quitting")
    exit(2010)

## Prepare deploy
global_schema = StateSchema(num_uints=global_num_uints, num_byte_slices=global_num_byte_slices)
local_schema = StateSchema(num_uints=local_num_uints, num_byte_slices=local_num_byte_slices)
suggested_params = algod_client.suggested_params()
tx = ApplicationCreateTxn(
    sender              = address,
    sp                  = suggested_params,
    on_complete         = OnComplete.NoOpOC,
    approval_program    = approval_program,
    clear_program       = clear_program,
    global_schema       = global_schema,
    local_schema        = local_schema,
    # accounts            =,                    ## The following parameters are not needed
    # foreign_apps        =,
    # foreign_assets      =,
    # note                =,
    # lease               =,
    # rekey_to            =,
    # extra_pages         =,
    # boxe                =,
)

try:
    signed_tx = tx.sign(private_key=private_key)
except Exception as e:
    print("💩 ", e)
    print("❌ Could not sign application transaction with private key ! Quitting")
    exit(1012)

start_time = timeit.default_timer()
try:
    tx_id = algod_client.send_transaction(signed_tx)
    print("🟢 Transaction ID: ", tx_id)
except Exception as e:
    print("💩 ", e)
    print("❌ Could not send application create transaction ! Quitting")
    exit(1013)

print("🕓 Wating for transaction to be confirmed...")
wait_for_confirmation(algod_client, tx_id)
elapsed = timeit.default_timer() - start_time
print(f"✅ Transaction confirmed! ({elapsed})")


'''
----------------------------------------------------------------------------------------------------    
    PART5: Closing phase: report data, fund the contract account, store it all in shevle, 
----------------------------------------------------------------------------------------------------    
'''

## Output results
tx_info = algod_client.pending_transaction_info(tx_id)                                  ## Note, the method is `pending` but works on confirmed transactions
app_id = tx_info['application-index']
application_address = get_application_address(app_id)
print("____________________________________________________________\n")
print("🔥 Application index:", app_id)
print("🔎 Lora Link: ", lora_link+'application/'+str(app_id))
print("📍 Application account:", lora_link+'account/'+application_address)
print("____________________________________________________________\n")

## Fund appliction address
print("🕓 Funding Application account...")
tx = PaymentTxn (
    sender=address,
    sp=suggested_params,
    receiver=application_address,
    amt=100_000
    # close_remainder_to=,
    # note=,
    # lease=,
    # rekey_to=,
)
start_time = timeit.default_timer()
try:
    signed_tx = tx.sign(private_key=private_key)
    tx_id = algod_client.send_transaction(signed_tx)
    wait_for_confirmation(algod_client, tx_id)
except Exception as e:
    print("💩 ", e)
    print("❌ Could not sign payment transaction with private key ! Quitting")
    exit(1014)
elapsed = timeit.default_timer() - start_time
print(f"✅ Funding confirmed! ({elapsed})")


## Store data into shelve
with shelve.open("shelve.db") as db:
    db['contract_name'] = contract_name
    db['application_address'] = application_address
    db['app_id'] = app_id
print("🏁 Done !! ")