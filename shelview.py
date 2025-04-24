#!/usr/bin/python3
import shelve

'''
----------------------------------------------------------------------------------------------------    
    This tool just dumps the content of the `shevles.db` file
    Use it to inspect the db if you want to see what's going on
----------------------------------------------------------------------------------------------------    
'''

with shelve.open("shelve.db") as db:
    keys = list(db.keys())
    for k in keys:
        print(f"{k}: {db[k]}")