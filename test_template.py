#!/usr/bin/python3

'''
    Generic pytest template for tests
    
    Since algopy_testing module simply simulate the AVM and DOES NOT allow you
    to test all transaction possible uses, you NEED to test the contract in a 
    real lagorand setup (localnet, testnet)
    
    Hence this module relies on the fact that the contract/app was deployed 
    using the other applications of this set and that the right values of the 
    app to test are in the shelve.db file.

    The first 270 lines or so take care of importing the values in a SharedState
    object that will be handled by the fixtures
    Afther that the code needs to be customized to fit the app you are testing

    For your convenience the `application_call` function is provided. You need 
    to pass it the SharedState object, name of the method, optional method
    parameters, optional transaction parameters (on_complete etc)

    Copy this file and modify the copy accordingly to your needs, then run it 
    with:
    
        pytest -v -s test_XXX.py
'''

import shelve
import pytest
import os
import re
import json
import importlib
import base64
from   pathlib import Path

from   algokit_utils.algorand import AlgorandClient, \
                                    AlgoClientConfigs, \
                                    AlgoClientNetworkConfig
from   algokit_utils import CommonAppCallParams, \
                            SendParams, \
                            AlgoAmount, \
                            SigningAccount


'''
----------------------------------------------------------------------------------------------------    
    Global variables
----------------------------------------------------------------------------------------------------    
'''

# MBR
# 1_000 for the 1 transactions
required_balance    = 1_000

'''
----------------------------------------------------------------------------------------------------    
    Shared State
    This class is used to pass contract info to and between the different tests
----------------------------------------------------------------------------------------------------    
'''

class SharedState:
    def __init__(self):
        self.data = {}
        
    def set(self, key, value):
        self.data[key] = value
        
    def get(self, key):
        return self.data.get(key)

'''
----------------------------------------------------------------------------------------------------    
    Fixtures
----------------------------------------------------------------------------------------------------    
'''

'''
    Define a SharedState instance ONCE for all other tests
'''
@pytest.fixture(scope="session", autouse=True)
def shared_state():
    return SharedState()



'''
    Get all initial values from shelves.db
    and perform some basic checks
'''
@pytest.fixture(scope="session", autouse=True)
def init(shared_state):
    ## Get values from shelves
    with shelve.open("shelve.db") as db:
        if 'private_key' in db and 'address' in db:
            shared_state.set('private_key', db['private_key'])
            shared_state.set('address', db['address'])
        if 'algod_address' in db:
            shared_state.set('algod_address', db['algod_address'])
        if 'algod_token' in db:
            shared_state.set('algod_token', db['algod_token'])
        if 'app_id' in db and db['app_id'] != None:
            shared_state.set('app_id', db['app_id'])
        if 'app_address' in db and db['app_address'] != None:
            shared_state.set('app_address', db['app_address'])
        if 'contract_name' in db and db['contract_name'] != None:
            shared_state.set('contract_name', db['contract_name'])
        if 'lora_link' in db:
            shared_state.set('lora_link', db['lora_link'])

    ## Get client module file and contract name
    directory = Path('./')
    client_module = list(directory.glob('*_client.py'))
    client_module = list(map(lambda x: str(x), client_module))[0]
    shared_state.set('client_module', client_module)
    shared_state.set('contract_name', client_module.replace('_client.py',''))

    ## Check that the contract client was created using alogkit-client-generator
    if os.path.exists(client_module) == True:
        module = importlib.import_module(client_module.replace('.py',''))
        shared_state.set('client_object', module)

    ## Connect to Algorand net via client
    # Define a network endpoint
    algo_net =AlgoClientNetworkConfig(
            server=shared_state.get('algod_address'),
            token=shared_state.get('algod_token')
    )
    # Use network entpoint to define the client
    algorand_client = AlgorandClient(AlgoClientConfigs(
            algod_config = algo_net,
            indexer_config = algo_net,
            kmd_config = algo_net
    ))
    shared_state.set('algorand_client',algorand_client)
    

    ## Get client module file and contract name
    abi_file = list(directory.glob(shared_state.get('contract_name')+'.arc56.json'))
    if len(abi_file) == 1:
        abi_file = list(map(lambda x: str(x), abi_file))[0]
        with open(abi_file) as f:
            shared_state.set('abi', json.loads(f.read()))

    ## Get a handler of the deployed HelloWord contract
    client_class = getattr(shared_state.get('client_object'), shared_state.get('contract_name')+'Client')
    app_client = algorand_client.client.get_typed_app_client_by_id(client_class , app_id = shared_state.get('app_id'))
    shared_state.set('client_class', client_class)
    shared_state.set('app_client', app_client)

    ## Create the signer that will sign the transaction to the SC
    signer = SigningAccount(private_key=shared_state.get('private_key'))
    algorand_client.account.set_signer_from_account(signer)
    shared_state.set('algorand_client', algorand_client)

    print(shared_state)


'''
    Print account info
'''
@pytest.fixture(scope="function")
def account_info(shared_state):
    private_key = shared_state.get('private_key')
    address = shared_state.get('address')
    algod_address = shared_state.get('algod_address')
    algod_token = shared_state.get('algod_token')
    algorand_client = shared_state.get('algorand_client')

    account_info = algorand_client.account.get_information(address)

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
    Query the app for it's details
    Note that this is done solely via the algorand_client, so this could be done
    with any app provided it's id
"""
@pytest.fixture(scope="function")
def app_info(shared_state):
    contract_name   = shared_state.get('contract_name')
    app_id  = shared_state.get('app_id')
    app_address = shared_state.get('app_address')
    algorand_client = shared_state.get('algorand_client')
    address = shared_state.get('address') 

    print(f"🔵 Using contract:    \"{contract_name}\"\t(app id: {app_id}, app address: {app_address})")
    box_names = algorand_client.app.get_box_names(app_id)
    for box in box_names:
        print(f"  🔹                  box {box.name}: {algorand_client.app.get_box_value(app_id, box.name)}")
    gs = algorand_client.app.get_global_state(app_id)
    for g in gs.keys():
        print(f"  🔹                  gbl {g}: {gs[g].value }")
    ls = algorand_client.app.get_local_state(app_id, address)
    for l in ls.keys():
        print(f"  🔹                  lcl {l}: {ls[l].value }")



'''
----------------------------------------------------------------------------------------------------    
    Functions
----------------------------------------------------------------------------------------------------    
'''

'''
   Makes a transaction
   Create and send the transaction to the application method
'''
def application_call(shared_state, sc_method, method_args = [], txn_args = []) :
    address = shared_state.get('address')
    app_client = shared_state.get('app_client')
    algorand_client = shared_state.get('algorand_client')

    app_method = getattr(app_client.send, sc_method)

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

    ## The client allows to pass the args as a tuple of strings
    if len(method_args) > 0:
        app_call_params['args'] = tuple(method_args)

    ## Send the transaction
    ## Use the spread operator to expand the object as function parameters
    res = app_method(**app_call_params)
    return res



'''
----------------------------------------------------------------------------------------------------    
    TESTS
----------------------------------------------------------------------------------------------------    
'''

## Fake initial test, just to test the fixtures and populate the shared_state
def test_go(shared_state, account_info, app_info):
    assert True


## Call the `get_version` method and compare abi return
def test_storage(shared_state):    
    res = application_call(shared_state, 'get_version')
    assert res.abi_return == 2