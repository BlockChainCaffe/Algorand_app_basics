#!/usr/bin/python3

import shelve
import os
import importlib
from   pathlib import Path

from   algosdk.v2client.algod import AlgodClient
from   algokit_utils.algorand import AlgorandClient, AlgoClientConfigs, AlgoClientNetworkConfig
from   algokit_utils import CommonAppCallParams, AlgoAmount, SigningAccount

import inspect


'''
----------------------------------------------------------------------------------------------------    
    The following 2 functions are used to inspect modules and classes/objects
----------------------------------------------------------------------------------------------------    
'''

def print_module_contents(module):
    print(f"\n📦 --- Functions in {module.__name__} ---")
    for name, item in inspect.getmembers(module, inspect.isfunction):
        print(f"🈸 Function: {name}")
    
    print(f"\n📦 --- Classes in {module.__name__} ---")
    for name, item in inspect.getmembers(module, inspect.isclass):
        # Filter out classes not defined in this module (optional)
        if item.__module__ == module.__name__:
            print(f"🔰 Class: {name}")
            # Print methods in the class
            print("⭐  Methods:")
            for method_name, method in inspect.getmembers(item, inspect.isfunction):
                if not method_name.startswith('__'):  # Skip magic methods
                    print(f"    - {method_name}")

def print_object_contents(obj):
    # Get the class name
    class_name = obj.__class__.__name__
    print(f"\n==== Object of class {class_name} ====")
    
    # Print attributes/parameters
    print("\n-- Attributes/Parameters --")
    for attr in dir(obj):
        # Skip private and magic attributes (those that start with _)
        if not attr.startswith('_'):
            # Get the value
            value = getattr(obj, attr)
            # Check if it's callable (a method) or an attribute
            if not callable(value):
                print(f"🧩 Attribute: {attr} = {value}")
    
    # Print methods
    print("\n-- Methods --")
    for attr in dir(obj):
        if not attr.startswith('_'):
            value = getattr(obj, attr)
            if callable(value):
                # Get the signature if it's a method
                try:
                    signature = inspect.signature(value)
                    print(f"⭐ Method: {attr}{signature}")
                except (ValueError, TypeError):
                    print(f"⭐ Method: {attr}()")


'''
----------------------------------------------------------------------------------------------------    
    PART 1: collect all the needed data to create classes
----------------------------------------------------------------------------------------------------    
'''


## Fundamental variables 
private_key         = None
address             = None

## Classes needed to interact with the network and contract
algod_address       = None
algod_token         = None
algod_client        = None 
algorand_client     = None
lora_link            = None

## Contract classes
contract_name       = None
app_id              = None
client_object       = None      ## This will contain the classes created in the *.client.py module (AppClient and AppFactory)
app_client          = None
signer              = None      ## Account derived from private key that will sign transactions

## Get values from shelves
with shelve.open("shelve.db") as db:
    if 'private_key' in db and 'address' in db:
        private_key = db['private_key']
        address = db['address']
        print("🟢 Using private key: ", private_key)
        print("🟢 Using address: ", address)
    else:
        print("❌ No account found in shelve.db. Create one first")
        exit(2001)

    if 'algod_address' in db:
        algod_address = db['algod_address']
        print("🟢 Using net: ", algod_address)
    else:
        print("❌ Algorand node address not specified")
        exit(2002)

    if 'algod_token' in db:
        algod_token = db['algod_token']
        print("🟢 Using token: ", algod_token)
    else:
        print("❌ Algorand token address not specified")
        exit(2003)

    if 'app_id' in db and db['app_id'] != None:
        app_id = db['app_id']
        print("🟢 Using app id: ", app_id)
    else:
        print("❌ Algorand token address not specified")
        exit(2005)

    if 'lora_link' in db:
        lora_link = db['lora_link']


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


## Store contract name in shelve
with shelve.open("shelve.db") as db:
    db['contract_name'] = contract_name


## Check that the contract client was created using alogkit-client-generator
if os.path.exists(client_module) != True:
    print("❌ Could not locate contract client! Quitting")
    exit(2006)
else:
    client_object = importlib.import_module(client_module.replace('.py',''))

## Check that account is correct
signer = SigningAccount(private_key=private_key)
if address != signer.address:
    print("❌ Private key and address dont' match")
    exit(2003)




'''
----------------------------------------------------------------------------------------------------    
    PART2 : connect to the network
----------------------------------------------------------------------------------------------------    
'''

## Connect to Algorand net via client
try:
    algod_client = AlgodClient(
        algod_address= algod_address,
        algod_token= algod_token
    )
    status = algod_client.status()
    if 'last-round' in status:
        print("✅ Connected")
        print("🕓 Last round: ", status['last-round'])
    
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
 
## If you want to examine the contents of client_object imported module, uncomment the following line
# print_module_contents(client_object)

## Get some account info (it's a check that we can speak to the node)
try:
    account_info = algod_client.account_info(address)
    print("💰 Account balance", account_info['amount']/1_000_000, "algos")
    print("🏦 Minimum balance", account_info['min-balance']/1_000_000, "algos")
except Exception as e:
    print("💩 ", e)
    print("❌ Could not get address info! Quitting")
    exit(1006)
if  (account_info['amount'] - account_info['min-balance']) < 1_000:
    print("💸 You are too poor! Quitting")
    exit(1007)



'''
----------------------------------------------------------------------------------------------------    
    PART3: Connect to the deployed app & use a method
----------------------------------------------------------------------------------------------------    
'''

## Get a handler of the deployed HelloWord contract
app_client = algorand_client.client.get_typed_app_client_by_id(client_object.HelloWorldContractClient , app_id = app_id)
## Uncomment the following line to inspect
# print_object_contents(app_client)

## Create the signer that will sign the transaction to the SC
signer = SigningAccount(private_key=private_key)
assert signer.address == address
## Set the singer into the AccountManager of Algorand Client
## this way the outgoing transaction sent by `address` will be authomatically signed
algorand_client.account.set_signer_from_account(signer)    

## Send the transaction to the `hello` method of the app
res = app_client.send.hello(
    # This is the parameter sent to the app method
    client_object.HelloArgs(
        name = "my friend"
    ),
    # These are the parameters needed for the transaction
    params = CommonAppCallParams(
            sender= address, 
            extra_fee=AlgoAmount(micro_algo=0)
    )
)

## Uncomment the following line to inspect
# print_object_contents(res)



'''
----------------------------------------------------------------------------------------------------    
    PART4: Show results
----------------------------------------------------------------------------------------------------    
'''

print("____________________________________________________________\n")
print(f"🟧 Abi return:      {res.abi_return}")
print(f"🟧 Confirmed round: {res.confirmation['confirmed-round']}")

print(f"🟧 Transactions     {len(res.transactions)}")
for n in range(len(res.transactions)):
    print(f" 🔶 Tx{n} tx_id:      {lora_link}transaction/{res.tx_ids[n]}")
    print(f"  🔸  App ID:       {res.confirmations[n]['txn']['txn']['apid']}")
    print(f"  🔸  Fee:          {res.confirmations[n]['txn']['txn']['fee']}")
    print(f"  🔸  Sender:       {res.confirmations[n]['txn']['txn']['snd']}")   
    print(f"  🔸  Type:         {res.confirmations[n]['txn']['txn']['type']}")
    match (res.confirmations[n]['txn']['txn']['type']) :
        case 'appl':
            print(f"  🔸  Note:         {res.transactions[0].application_call.note}")

print("____________________________________________________________\n")

