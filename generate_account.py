#!/usr/bin/python3

## Old way of generating account
# from algosdk.account import generate_account
# private_key, address = generate_account()

import shelve
from   algokit_utils.algorand import AlgorandClient

## Check if an address is already there
with shelve.open("shelve.db") as db:
    if 'private_key' in db and 'address' in db:
        print("🟨 The following account is already available:")
        print("🟨 Private key: ", db['private_key'])
        print("🟨 Address: ", db['address'])
        overwrite = input("Erase and overwrite account? (Y/*)")
        if overwrite != 'Y' :
            print("❌ Exiting")
            exit(0)

## Generate new random account
# Create an algorand client from environment
# we don't care about a proper client with proper connection
# since we just want a random account that can work on any net.
algorand = AlgorandClient.from_environment()
signer = algorand.account.random()

print("🟢 New Private key: ", signer.private_key)
print("🟢 New Address: ", signer.address)

## Save to shelve db
with shelve.open("shelve.db") as db:
    db['private_key'] = signer.private_key
    db['address'] = signer.address

print("\n🏁 Account generated")