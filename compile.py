import os
import sys
import shelve
from   pathlib import Path


contract = sys.argv[1]
os.system(f"algokit compile python {contract} --output-arc56")
directory = Path('./')
contract_name = list(directory.glob('*.arc56.json'))
contract_name = list(map(lambda x: str(x), contract_name))
contract_name = contract_name[0].replace('.arc56.json','')
os.system(f"algokitgen-py -a {contract_name}.arc56.json -o {contract_name}_client.py")


with shelve.open("shelve.db") as db:
    db['contract_name'] = contract_name