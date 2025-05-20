#!/usr/bin/python3

import shelve
import os
import re
import json
import importlib
import textwrap
import shutil
import base64
from   pathlib import Path

from   algokit_utils.algorand import AlgorandClient, \
                                    AlgoClientConfigs, \
                                    AlgoClientNetworkConfig
from   algokit_utils import CommonAppCallParams, \
                            SendParams, \
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

## Interface
window_width        = shutil.get_terminal_size().columns

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
    },
}
## MBR
# 1_000 for the 1 transactions
required_balance    = 1_000

'''
----------------------------------------------------------------------------------------------------    
    Helper functions
----------------------------------------------------------------------------------------------------    
'''

"""
    Just draw a line as wide as the console
"""
def _line():
    print(f"_"*window_width)


"""
    Clear the screen
"""
def cls():    # Clear console based on the operating system
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Unix/Linux/Mac
        os.system('clear')


'''
----------------------------------------------------------------------------------------------------    
    Main functions
----------------------------------------------------------------------------------------------------    
'''

'''
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



'''
    Print header account info
'''
def _account_info():
    global private_key
    global address
    global algod_address
    global algod_token
    global app_id
    global contract_name
    global algorand_client

    account_info = algorand_client.account.get_information(address)

    cls()
    print(f"🚀 Using net:         {algod_address}\tToken: {algod_token}")
    print(f"🔑 Using address:     {address}")
    print(f"   Using private key: {private_key}")
    print(f"💰 Account balance    {account_info.amount.micro_algo/1_000_000} algos\t(MBR: {account_info.min_balance.micro_algo /1_000_000} algos)")
    if  (account_info.amount.micro_algo - account_info.min_balance.micro_algo)< required_balance:
        print("🔴 You are too poor! ")
    try:
        if account_info.created_apps :
            created = list(map(lambda x : x['id'], account_info.created_apps))
            print(f"🔧 Apps created       {created}")
        
        if account_info.total_apps_opted_in > 0 :
            opted = []
            print(f"👍 Apps opted in:")
            for o in range(account_info.total_apps_opted_in):
                opted.append(account_info.apps_local_state[o]['id'])
                if 'key-value' in account_info.apps_local_state[o] :
                    for kv in account_info.apps_local_state[o]['key-value']:
                        key = decoded_bytes = base64.b64decode(kv['key']).decode("utf-8")
                        print(f"                      {account_info.apps_local_state[o]['id']} : {key} = {kv['value']}")
                else:
                    print(f"                      {account_info.apps_local_state[o]['id']}")
    except Exception as e:
        print("💩 ", e)
        print("❌ Could not get address info! Quitting")
        exit(1006)


"""
    Gets the methods of the contract (from the ARC56.json file) and
    parse them into a dictionary for later convenience
"""
def _parse_methods():
    global methods

    parsed={}
    for m in methods:
        signature = {}
        signature['returns'] = m['returns']['type']
        signature['args'] = m['args']
        signature['actions'] = m['actions']
        parsed[m['name']] = signature
        if 'desc' in m:
            signature['desc'] = m['desc']
    methods = {**parsed}


"""
    Get the on_completed and create parameters of the method call
    and output a short string to present them to the user
    Please note that just OptIn is taken care of ATM
"""
def _parse_actions(act):
    oc = ''
    cr = ''

    if "OptIn" in act['call']:
        oc+='1'
    if "DeleteApplication" in act['call']:
        oc+='5'

    if len(cr) :
        cr = 'cr='+cr+'/'
    if len(oc) :
        oc = 'oc='+oc
    return f"[{cr}{oc}]" if (len(cr)+len(oc)>0) else ''


"""
    Query the app for it's details
    Note that this is done solely via the algorand_client, so this could be done
    with any app provided it's id
"""
def _show_app_details():
    _line()
    print(f"🔵 Using contract:    \"{contract_name}\"\t(app id: {app_id}, app address: {app_address})")
    
    try:
        box_names = algorand_client.app.get_box_names(app_id)
        for box in box_names:
            print(f"  🔹                  box {box.name}: {algorand_client.app.get_box_value(app_id, box.name)}")
    except Exception as e:
        print(f"  🔹                  no boxes")     

    try:
        gs = algorand_client.app.get_global_state(app_id)
        for g in gs.keys():
            print(f"  🔹                  gbl {g}: {gs[g].value }")
    except Exception as e:
        print(f"  🔹                  no globals")     
    
    try:
        ls = algorand_client.app.get_local_state(app_id, address)
        for l in ls.keys():
            print(f"  🔹                  lcl {l}: {ls[l].value }")
    except Exception as e:
        print(f"  🔹                  no locals")     


"""
    Display the app methods and it's parameters
"""
def _show_methods():
    global methods
    _line
    print(f"🟦 Contract methods:")
    for key, val in methods.items():
        args = '' 
        for a in val['args']:
            args = f"{a['type']}:{a['name']}"
        rets = f"{val['returns']}"
        act = _parse_actions(val['actions'])
        print(f"  🔹 {key} ({args}) -> {rets}\t{act}")
        if 'desc' in val:
            indent = ' '*(len(key)+4)
            wrapper = textwrap.TextWrapper(initial_indent=indent, subsequent_indent=indent)
            print(wrapper.fill(f"{val['desc']}"))
        for a in val['args']:
            if 'desc' in a:
                print(f"    \t🔹 {a['type']}:{a['name']} {a['desc']}")
    _line()
    print("🟦 Generic tx:")  
    print(f"  🔹 payment (receiver:address, amount:uint64) -> uint64")
    _line()
    print("🟦 Txn Parameters")  
    print(f"  🔹 on_complete:<NoOp=0/OptIn/CloseOut/Clearstate/UpdateApplication/DeleteApplication=5>")



'''
   Present the details of a performed transactions
   Note: Algorand is very peculiar with all the transaction types
   Not all transactions will return the same data with the same object etc
   This function might fail because some parameters are not present
'''
def _tx_output(res):
    _line()

    res_class_name = res.__class__.__name__

    print(f"🟧 Return type:     {res_class_name}")
    if hasattr(res, 'abi_return'):
        print(f"🟧 Abi return:      {res.abi_return}")
    if res_class_name == 'SendSingleTransactionResult' :
        print(f"🟧 Amount:          {res.transactions[0].payment.amt}")
    if hasattr(res,'confirmation') and hasattr(res.confirmation, 'confirmed-round'):
        print(f"🟧 Confirmed round: {res.confirmation['confirmed-round']}")
    print(f"🟧 Transactions     {len(res.transactions)}")
    for n in range(len(res.transactions)):
        print(f" 🔶 Tx{n} tx_id:      {lora_link}transaction/{res.tx_ids[n]}")
        print(f"  🔸  Sender:       {res.confirmations[n]['txn']['txn']['snd']}")
        if hasattr(res.confirmations[n]['txn']['txn'], 'rcv'):
            print(f"  🔸  Receiver:     {res.confirmations[n]['txn']['txn']['rcv']}")
        print(f"  🔸  Type:         {res.confirmations[n]['txn']['txn']['type']}")
        print(f"  🔸  Fee:          {res.confirmations[n]['txn']['txn']['fee']}")
        if 'apid' in res.confirmations[n]['txn']['txn']:
            print(f"  🔸  App ID:       {res.confirmations[n]['txn']['txn']['apid']}")
        match (res.confirmations[n]['txn']['txn']['type']) :
            case 'appl':
                print(f"  🔸  Note:         {res.transactions[0].application_call.note}")

    print("\n")
    input(f"✅ Press any key to continue")



'''
   Makes a transaction
   Create and send the transaction to the application method
'''
def do_method_tx(sc_method, method_args, txn_args) :
    global address
    global methods

    # Why the hell the client needs to be so complicated
    # and hide methods in different places?
    app_method = None
    if hasattr(app_client.send, sc_method):
        app_method = getattr(app_client.send, sc_method)
    elif hasattr(app_client.send.delete, sc_method):
        app_method = getattr(app_client.send.delete, sc_method)
    elif hasattr(app_client.send.opt_in, sc_method):
        app_method = getattr(app_client.send.opt_in, sc_method)

    ## Get last blockchain round (See later)
    last_round = algorand_client.client.algod.status()['last-round']

    ## Turn txn_args into a dictionary to ease the creation of CommonAppCallParams class object
    cacp = {}
    cacp['sender'] = address 
    cacp['extra_fee'] =AlgoAmount(micro_algo=0)
    ## To avoid the "transaction is already in ledger" error we tweak the validity rounds
    ## parameter so to have always new transactions
    cacp['first_valid_round'] = last_round
    cacp['last_valid_round'] = last_round +1000


    ## Parse the transactions parameters like
    ## ex:  string "on_complete:1" becomes dict {'on_complete':1}
    ##      and gets later passed to the ApplicationCall
    for txn_a in txn_args:
        arg_key = re.sub(':.*$','', txn_a)
        arg_value = re.sub('^.*:','', txn_a)
        if arg_value.isnumeric():
            arg_value = int(arg_value)
        cacp[arg_key]=arg_value

    # These are the parameter sent to the app call
    app_call_params={
        'params' : CommonAppCallParams(**cacp),
        # From algokit-utils >= 4.0.0 the followin line will not be necessary
        'send_params' : SendParams(populate_app_call_resources=True),
    }

    ## Conditionally add the method_args to app call if any
    if len(method_args) > 0 :
        # Convert input to proper type
        args = methods[sc_method]['args']
        for n in range(len(method_args)) :
            # which destination type?
            match args[n]['type']:
                case 'uint64':
                    ## If parameter is uint64 turn string -> int
                    method_args[n] = int(method_args[n])

    ## The client allows to pass the args as a tuple of strings
    if len(method_args) > 0:
        app_call_params['args'] = tuple(method_args)

    ## Send the transaction
    try :
        ## Use the spread operator to expand the object as function parameters
        res = app_method(**app_call_params)
        return res
    except Exception as e:
        print(f"❌ {e}")
        input(f"🔻 Press any key to continue")
        return False


"""
    Perform a generic transaction (ie: non related to the application)
"""
def do_generic_tx(sc_method, method_args, txn_args) :
    global address
    try:
        if sc_method == 'payment' :
            res = algorand_client.send.payment (
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


"""
    Get the transaction and send it to the proper handler
"""
def dotx(sc_method, method_args, txn_args):
    if sc_method in methods.keys():
        return do_method_tx(sc_method, method_args, txn_args)
    elif sc_method in generic_tx.keys():
        return do_generic_tx(sc_method, method_args, txn_args)
    else:
        return False


"""
    Check the user's input
    If it's a method call, verify the number of parameters matches the one of the ABI
"""
def _check_sel(sc_method, method_args, txn_args):
    global methods

    # Check if is a valid method 
    if sc_method in methods.keys():
        # Check if supplied parameters are in the right number
        if len(methods[sc_method]['args']) != len(method_args):
            print(f"🔺 Please supply right number of parameters: {len(methods[sc_method]['args'])}")
            input(f"🔻 Press any key to continue")
            return False
    elif sc_method in generic_tx.keys():
        if len(generic_tx[sc_method]['args']) != len(method_args):
            print(f"🔺 Please supply right number of parameters: {len(generic_tx[sc_method]['args'])}")
            input(f"🔻 Press any key to continue")
            return False
    else :
        print(f"🔺 {sc_method} is not a valid method/transaction")
        input(f"🔻 Press any key to continue")
        return False

    # Check Txn_params
    allowed_params = ['on_complete']
    for txn_a in txn_args:
        arg_key = re.sub(':.*$','', txn_a)
        arg_value = re.sub('^.*:','', txn_a)
        if not arg_key in allowed_params:
            print(f"🔺 {arg_key} is not a valid transaction parameterset_l ")
            input(f"🔻 Press any key to continue")
            return False
        
        if arg_key == 'on_complete':
            ## Value must be 0..5
            arg_value = int(arg_value)
            if arg_value < 0 or arg_value > 5 :
                print(f"🔺 {arg_value} is not a valid integer in 0..5 ")
                input(f"🔻 Press any key to continue")
                return False

    return True
    

"""
    Get input from user
"""
def _input():
    print("\nInsert name of method and parameters to send application call")
    print("[Q] to exit")
    sel = input("▶ ")
    if sel == 'Q' or sel == 'q':
        return False
    return sel


"""
    Main loop
    - Show account_info, app details, methods
    - get user input
    - parse it
"""
def _loop():
    sel = True
    while sel != False:
        _account_info()
        _show_app_details()
        _show_methods()
        sel = _input()
        if not sel:
            continue

        ## Split the input in it's parts: method called, method arguments, optional tx parameters
        sel = re.sub(r'\s+', ' ', sel)
        sel = sel.split(" ")    
        sc_method = sel[0]
        method_args = list(filter(lambda a : False if ':' in a else True, sel[1:]))
        txn_args = list(filter (lambda a : True if ':' in a else False, sel[1:]))

        ## Check the input
        call = _check_sel(sc_method, method_args, txn_args)
        if call == False:
            continue

        ## Handle the transaction
        res = dotx(sc_method, method_args, txn_args)
        if res : 
            ## Display result
            _tx_output(res)


"""________________________________________________________________________

   MAIN
"""

def main():
    _init()
    _parse_methods()
    _loop()


if __name__ == "__main__": 
    main()