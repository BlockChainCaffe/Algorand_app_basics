#!/usr/bin/python3

import shelve

algod_address = None
algod_token = None

with shelve.open("shelve.db") as db:
    if 'algod_address' in db or 'algod_token' in db:
        print("🟨 The following network is already defined:")
        print("🟨 Address: ", db['algod_address'])
        print("🟨 Token: ", db['algod_token'])
        overwrite = input("Erase and overwrite network? (Y/*)")
        if overwrite != 'Y' :
            print("❌ Exiting")
            exit(1001)

print("Select your destination network: ")
print("1) docker/algokit Localnet on port 4001")
print("2) Testnet (via free nodely.io node)")
print("3) Mainnet (via free nodely.io node)")
net = int(input ("\n❓ pick one: "))


match net:
    # Localnet
    case 1 :
        algod_address = 'http://localhost:4001'
        algod_token = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        lora_link = 'https://lora.algokit.io/localnet/'
    # Testnet
    case 2 :
        algod_address = 'https://testnet-api.4160.nodely.dev'
        algod_token = ''
        lora_link = 'https://lora.algokit.io/testnet/'
    # Mainnet
    case 3 :
        algod_address = 'https://mainnet-api.4160.nodely.dev'
        algod_token = ''
        lora_link = 'https://lora.algokit.io/mainnet/'
    case _ :
        print("❌ Wrong selection, aborting")
        exit(1002)

## Save to shelve db
with shelve.open("shelve.db") as db:
    db['algod_address'] = algod_address
    db['algod_token'] = algod_token
    db['lora_link'] = lora_link

print("\n🏁 Network set")