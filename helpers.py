import inspect
import os

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




def cls():    # Clear console based on the operating system
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Unix/Linux/Mac
        os.system('clear')