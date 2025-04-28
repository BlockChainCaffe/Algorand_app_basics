#!/usr/bin/python3

import shelve
import timeit
import os
import importlib
from   pathlib import Path
from   base64 import b64decode

from algokit_utils import SigningAccount, PaymentParams, AlgoAmount
from algokit_utils.algorand import AlgorandClient, AlgoClientConfigs, AlgoClientNetworkConfig

'''
----------------------------------------------------------------------------------------------------    
    Variables we'll be using
----------------------------------------------------------------------------------------------------    
'''

## Globals initialized by shelve.db
private_key             = None
address                 = None
algod_address           = None
algod_token             = None
lora_link               = None

## Classess used to connect to blockchain and deploy
algorand_client         = None
contract_name           = None
signer                  = None

## Compile and deploy parameters/values/files
teal_approval_file      = None      # Teal programs
teal_clear_file         = None      
client_object           = None      # Client for the smart contract

## Results (to be saved in shelves.db)
app_id                  = None
app_address             = None

## MBR
# 100_000 for the creator MBR,
# 100_000 to fund the application address MBR, 
# 2_000 for the 2 transactions
required_balance        = 202_000


'''
----------------------------------------------------------------------------------------------------    
    PART1: get all data & info needed to deploy the contract
----------------------------------------------------------------------------------------------------    
'''

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

## Connect to Algorand net via client
try:
    # Define a network endpoint
    algo_net =AlgoClientNetworkConfig(
            server=algod_address,
            token=algod_token
    )
    # Use network entpoint to define the client
    algorand_client = AlgorandClient(AlgoClientConfigs(
        algod_config = algo_net,
        indexer_config = algo_net,
        kmd_config = algo_net
    ))
except Exception as e:
    print("💩 ", e)
    print("❌ Could not connet! Quitting")
    exit(2004)

## Get some account info (it's a check that we can speak to the node)
try:
    account_info = algorand_client.account.get_information(address)
    print("💰 Account balance", account_info.amount.micro_algo/1_000_000, "algos")
    print("🏦 Minimum balance", account_info.min_balance.micro_algo /1_000_000, "algos")
except Exception as e:
    print("💩 ", e)
    print("❌ Could not get address info! Quitting")
    exit(1006)
if  (account_info.amount.micro_algo - account_info.min_balance.micro_algo)< required_balance:
    print("💸 You are too poor! Quitting")
    exit(1007)


'''
----------------------------------------------------------------------------------------------------    
    PART3: Load the .py client 
----------------------------------------------------------------------------------------------------    
'''

## Get client module file and contract name
try:
    directory = Path('./')
    client_module = list(directory.glob('*_client.py'))
    client_module = list(map(lambda x: str(x), client_module))
    if len(client_module) != 1:
        print("❌ Exaclty 1 Client file expected ! Quitting")
        exit(2008)
    else:
        client_module = client_module[0]
        contract_name = client_module.replace('_client.py','')
except Exception as e:
    print("💩 ", e)
    print("❌ Error finding client file! Quitting")

## Check that the contract client was created using alogkit-client-generator
if os.path.exists(client_module) != True:
    print("❌ Could not locate contract client! Quitting")
    exit(2006)
else:
    client_object = importlib.import_module(client_module.replace('.py',''))


'''
----------------------------------------------------------------------------------------------------    
    PART4: Compile the contract for deploy
----------------------------------------------------------------------------------------------------    
'''

## Get contract factory from client, use reflection to import factory
factory_method = getattr(client_object, contract_name+'Factory')
factory = factory_method(
    algorand = algorand_client,
    default_sender = signer.address,
    default_signer = signer
)
print(factory)

print("🕓 Creating and Deplying contract...")
start_time = timeit.default_timer()
try:
    app_client, deploy_response = factory.send.create.bare()
    app_id = app_client.app_id
    app_address = app_client.app_address
    
except Exception as e:
    print("💩 ", e)
    print("❌ Could not deploy contract ! Quitting")
    exit(1013)

print('🟢 Contract Deployed!')
# wait_for_confirmation(algod_client, tx_id)
elapsed = timeit.default_timer() - start_time
print(f"✅ Deploy successful! ({elapsed})")

print("____________________________________________________________\n")
print(f"🔥 Application ID:{app_id}")
print(f"📍 Application Address: {lora_link+'account/'+app_address}")
print(f"🔗 Lora Link: {lora_link+'application/'+str(app_id)}")
print(f"🔎 Deploy Transaction ID: {deploy_response.tx_ids[0]}")
print("____________________________________________________________\n")


'''
----------------------------------------------------------------------------------------------------    
    PART6: Closing phase: Fund the contract account, store it all in shevle, 
----------------------------------------------------------------------------------------------------    
'''

## Fund appliction address
print("🕓 Funding Application account...")

start_time = timeit.default_timer()
try:
    fund = algorand_client.send.payment(
        params=PaymentParams(
            sender=address,
            signer=signer,
            amount=AlgoAmount(algo=0.1),
            receiver=app_client.app_address,
        )
    )
except Exception as e:
    print("💩 ", e)
    print("❌ Could not sign payment transaction with private key ! Quitting")
    exit(1014)

elapsed = timeit.default_timer() - start_time
print(f"🔎 Funding Transaction ID: {fund.tx_ids[0]}")
print(f"🔎 Transaction amount: {fund.confirmation['txn']['txn']['amt']}")
print(f"🔎 Transaction fee: {fund.confirmation['txn']['txn']['fee']}")
print(f"🔎 Transaction type: {fund.confirmation['txn']['txn']['type']}")

print(f"✅ Funding confirmed! ({elapsed})")


## Store data into shelve
with shelve.open("shelve.db") as db:
    db['contract_name'] = contract_name
    db['app_address'] = app_address
    db['app_id'] = app_id
print("🏁 Done !! ")