#!/usr/bin/python3

import shelve
import os
import re
import json
import importlib
import textwrap
from   pathlib import Path

from   algosdk.v2client.algod import AlgodClient
from   algokit_utils.algorand import AlgorandClient, \
                                    AlgoClientConfigs, \
                                    AlgoClientNetworkConfig
from   algokit_utils import CommonAppCallParams, \
                            AlgoAmount, \
                            SigningAccount, \
                            PaymentParams

from helpers import print_module_contents, \
                    print_object_contents, \
                    cls

'''
----------------------------------------------------------------------------------------------------    
    Global variables
----------------------------------------------------------------------------------------------------    
'''


## Fundamental variables 
private_key         = None
address             = None

## Classes needed to interact with the network and contract
algod_address       = None
algod_token         = None
algorand_client     = None
lora_link           = None

## Contract classes
contract_name       = None
app_id              = None
client_object       = None      ## This will contain the classes created in the *.client.py module (AppClient and AppFactory)
app_client          = None
app_address         = None
signer              = None      ## Account derived from private key that will sign transactions
abi                 = None      ## ABI object of contract
methods             = None      ## ABI methods

# Generic transactions that can be sent regardless of smart contract methods
generic_tx          = {
    'payment' : {
        'returns' : 'uint64',
        'args': [
            {
                'name':'receiver',
                'type':'address',
                'desc':'The destionation account'
            },
            {
                'name':'amount',
                'type':'AlgoAmount',
                'desc':'Amount to send'
            }
        ]
    }
}
## MBR
# 1_000 for the 1 transactions
required_balance    = 1_000


''' ___________________________________________________________________________

    Get all initial values from shelves.db
    and perform some basic checks
'''
def _init():
    global private_key
    global address
    global algod_address
    global algod_token
    global app_id
    global app_address
    global contract_name
    global algorand_client
    global lora_link
    global client_object
    global app_client
    global signer
    global abi
    global methods

    ## Get values from shelves
    with shelve.open("shelve.db") as db:
        if 'private_key' in db and 'address' in db:
            private_key = db['private_key']
            address = db['address']
        else:
            print("❌ No account found in shelve.db. Create one first")
            exit(2001)

        if 'algod_address' in db:
            algod_address = db['algod_address']
        else:
            print("❌ Algorand node address not specified")
            exit(2002)

        if 'algod_token' in db:
            algod_token = db['algod_token']
        else:
            print("❌ Algorand token address not specified")
            exit(2003)

        if 'app_id' in db and db['app_id'] != None:
            app_id = db['app_id']
        else:
            print("❌ Algorand token address not specified")
            exit(2005)

        if 'app_address' in db and db['app_address'] != None:
            app_address = db['app_address']
        else:
            print("❌ Algorand app address not specified")
            exit(2005)

        if 'contract_name' in db and db['contract_name'] != None:
            contract_name = db['contract_name']
        else:
            print("❌ Contract name not specified")
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

    ## Get client module file and contract name
    try:
        directory = Path('./')
        abi_file = list(directory.glob(contract_name+'.arc56.json'))
        if len(abi_file) != 1:
            print("❌ Exaclty 1 arc56 ABI file expected ! Quitting")
            exit(2008)
        else:
            abi_file = list(map(lambda x: str(x), abi_file))[0]
    except Exception as e:
        print("💩 ", e)
        print("❌ Error finding client file! Quitting")

    with open(abi_file) as f:
        abi = json.loads(f.read())
    methods = abi['methods']

    ## Get a handler of the deployed HelloWord contract
    client_class = getattr(client_object, contract_name+'Client')
    app_client = algorand_client.client.get_typed_app_client_by_id(client_class , app_id = app_id)
    ## Uncomment the following line to inspect
    # print_object_contents(app_client)

    ## Create the signer that will sign the transaction to the SC
    signer = SigningAccount(private_key=private_key)
    assert signer.address == address
    ## Set the singer into the AccountManager of Algorand Client
    ## this way the outgoing transaction sent by `address` will be authomatically signed
    algorand_client.account.set_signer_from_account(signer)    



''' ___________________________________________________________________________

    Print header banner with basic info
'''
def _banner():
    global private_key
    global address
    global algod_address
    global algod_token
    global app_id
    global contract_name
    global algorand_client


    cls()
    print(f"🟢 Using private key: {private_key}")
    print(f"🟢 Using address:     {address}")
    print(f"🟢 Using net:         {algod_address}")
    print(f"🟢 Using token:       {algod_token}")
    print(f"🟢 Using contract:    {contract_name}")
    print(f"🟢 Using app id:      {app_id}")
    print(f"🟢 Using app address: {app_address}")
          
    try:
        account_info = algorand_client.account.get_information(address)
        print(f"💰 Account balance    {account_info.amount.micro_algo/1_000_000,} algos")
        print(f"🏦 Minimum balance    {account_info.min_balance.micro_algo /1_000_000} algos")
    except Exception as e:
        print("💩 ", e)
        print("❌ Could not get address info! Quitting")
        exit(1006)
    if  (account_info.amount.micro_algo - account_info.min_balance.micro_algo)< required_balance:
        print("💸 You are too poor! Quitting")
        exit(1007)


def _parse_methods():
    global methods

    parsed={}
    for m in methods:
        signature = {}
        signature['returns'] = m['returns']['type']
        signature['args'] = m['args']
        parsed[m['name']] = signature
        if 'desc' in m:
            signature['desc'] = m['desc']
    methods = {**parsed}


def _show_methods():
    global methods
    print("____________________________________________________________\n")
    print("🟦 Contract methods:")
    for key, val in methods.items():
        args = '' 
        for a in val['args']:
            args = f"{a['type']}:{a['name']}"
        rets = f"{val['returns']}"
        print(f"  🔹 {key} ({args}) -> {rets}")
        if 'desc' in val:
            indent = ' '*(len(key)+4)
            wrapper = textwrap.TextWrapper(initial_indent=indent, subsequent_indent=indent)
            print(wrapper.fill(f"{val['desc']}"))
        for a in val['args']:
            if 'desc' in a:
                print(f"    \t🔹 {a['type']}:{a['name']} {a['desc']}")
        print()
    print("____________________________________________________________\n")
    print("🟦 Generic tx:")  
    print(f"  🔹 payment (receiver:address, amount:uint64) -> uint64")
    print()

''' ___________________________________________________________________________

   Present the details of a performed transactions
'''
def _tx_output(res):
    print("____________________________________________________________\n")\

    res_class_name = res.__class__.__name__

    print(f"🟧 Return type:     {res_class_name}")
    if hasattr(res, 'abi_return'):
        print(f"🟧 Abi return:      {res.abi_return}")
    if res_class_name == 'SendSingleTransactionResult' :
        print(f"🟧 Amount:          {res.transactions[0].payment.amt}")
    print(f"🟧 Confirmed round: {res.confirmation['confirmed-round']}")
    print(f"🟧 Transactions     {len(res.transactions)}")
    for n in range(len(res.transactions)):
        print(f" 🔶 Tx{n} tx_id:      {lora_link}transaction/{res.tx_ids[n]}")
        print(f"  🔸  Sender:       {res.confirmations[n]['txn']['txn']['snd']}")
        print(f"  🔸  Receiver:     {res.confirmations[n]['txn']['txn']['rcv']}")
        print(f"  🔸  Type:         {res.confirmations[n]['txn']['txn']['type']}")
        print(f"  🔸  Fee:          {res.confirmations[n]['txn']['txn']['fee']}")
        if 'apid' in res.confirmations[n]['txn']['txn']:
            print(f"  🔸  App ID:       {res.confirmations[n]['txn']['txn']['apid']}")
        match (res.confirmations[n]['txn']['txn']['type']) :
            case 'appl':
                print(f"  🔸  Note:         {res.transactions[0].application_call.note}")

    print("____________________________________________________________\n")
    input(f"✅ Press any key to continue")


''' ___________________________________________________________________________

   Makes a transaction
'''
def do_method_tx(method_name, method_args) :
    global address

    app_method = getattr(app_client.send, method_name)
    ## Send the transaction to the `hello` method of the app

    # This is the parameter sent to the app call
    app_call_params={
        'params' : CommonAppCallParams(
            sender= address, 
            extra_fee=AlgoAmount(micro_algo=0)
        )
    }

    # Conditionally add the method_args to app call if any
    if len(method_args) > 0 :
        # The client allows to use a tuple of strings !!
        app_call_params['args'] = tuple(method_args)

    # Use the spread operator to expand the object as function parameters
    try :
        res = app_method(**app_call_params)
        return res
    except Exception as e:
        print(f"❌ {e.message}")
        input(f"🔻 Press any key to continue")
        return False


def do_generic_tx(method_name, method_args) :
    global address

    try:
        if method_name == 'payment' :
            res = algorand_client.send.payment(
                PaymentParams(
                    sender =  address,
                    receiver = method_args[0],
                    amount = AlgoAmount(micro_algo=method_args[1])
                )
            )
            return res
    except Exception as e:
        print(f"❌ {e.message or e}")
        input(f"🔻 Press any key to continue")

    return False


def dotx(method_name, method_args):
    if method_name in methods.keys():
        return do_method_tx(method_name, method_args)
    elif method_name in generic_tx.keys():
        return do_generic_tx(method_name, method_args)
    else:
        return False


def _input():
    print("Insert name of method and parameters to send application call")
    print("[Q] to exit]")
    sel = input("▶ ")
    if sel == 'Q' or sel == 'q':
        return False
    return sel


def _check_sel(sel):
    global methods

    sel = re.sub(r'\s+', ' ', sel)
    sel = sel.split(" ")
    # Check if is a valid method 
    if sel[0] in methods.keys():
        # Check if supplied parameters are in the right number
        if len(methods[sel[0]]['args'])+1 == len(sel):
            return sel
        print(f"🔺 Please supply right number of parameters: {len(methods[sel[0]]['args'])}")
        input(f"🔻 Press any key to continue")
        return False
    elif sel[0] in generic_tx.keys():
        if len(generic_tx[sel[0]]['args'])+1 == len(sel):
            return sel
        print(f"🔺 Please supply right number of parameters: {len(generic_tx[sel[0]]['args'])}")
        input(f"🔻 Press any key to continue")
        return False
    else :
        print(f"🔺 {sel[0]} is not a valid method/transaction")
        input(f"🔻 Press any key to continue")
        return False

    

def _menu():
    sel = True
    while sel != False:
        _banner()
        _show_methods()
        sel = _input()
        if not sel:
            continue
        call = _check_sel(sel)
        if call == False:
            continue
        res = dotx(call[0], call[1:])
        if res : 
            _tx_output(res)


''' ___________________________________________________________________________

   MAIN
'''

def main():
    _init()
    _parse_methods()
    _menu()


if __name__ == "__main__": 
    main()