#!/usr/bin/python3
import shelve
import sys

## Set by generate_account.py
# private_key: U28djzPz2JGyxCeLMbrMBHsF6M805NleYepQRfR+E3Jugs+VjSmyARRxNhwwVkuq01kae5/ZuG/wtFKlGOkxmg==
# address: N2BM7FMNFGZACFDRGYODAVSLVLJVSGT3T7M3Q37QWRJKKGHJGGNDEU7TRM

## Set by set_network
# algod_token: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
# algod_address: http://localhost:4001
# lora_link: https://lora.algokit.io/localnet/

## Set by deploy
# app_id: 1085
# application_address: 2MLRYF3DBSFDDNBOGFRREKCNP7RSRBLLQ3IBP3NLISJW5G65UXQXEETOW4
# contract_name: HelloWorldContract

'''
------------------------------------------------------------------------
    Use this script to clean stuff that may end up in the shelves.db
------------------------------------------------------------------------
'''

key = sys.argv[1]

with shelve.open("shelve.db") as db:
    # Remove these
    if key in db:
        del db[key]
