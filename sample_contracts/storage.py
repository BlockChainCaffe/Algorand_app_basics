from algopy import Account, ARC4Contract, BoxMap, Global, Txn, UInt64, gtxn, itxn, Box, LocalState
from algopy.arc4 import abimethod


class Storage(ARC4Contract):

    def __init__(self) -> None:
        """
        Create storage options
        """

        # Box
        self.st_box = Box(UInt64)
        # Global
        self.st_global = UInt64()
        # Local
        self.st_local = LocalState(UInt64)


    """----------------------------------------------------
        Set Functions
    """
    @abimethod()
    def set_b(self, data:UInt64) -> UInt64:
        self.st_box.value = data
        return self.st_box.value

    @abimethod()
    def set_g(self, data:UInt64) -> UInt64:
        self.st_global = data
        return self.st_global

    @abimethod()
    def set_l(self, data:UInt64) -> UInt64:
        self.st_local[Txn.sender] = data
        return self.st_local[Txn.sender]


    """----------------------------------------------------
        Get Functions
        Remeber to set readonly=True for all 'pure/view' methods
    """
    @abimethod(readonly=True)
    def get_b(self) -> UInt64:
        val, ex = self.st_box.maybe()
        return val if ex else UInt64(0)    

    @abimethod(readonly=True)
    def get_g(self) -> UInt64:
        return self.st_global

    @abimethod(readonly=True)
    def get_l(self) -> UInt64:
        return self.st_local[Txn.sender]

    """----------------------------------------------------
        Contract Version
        Note: this method allows the user to opt-in.
        It is mandatory for the user to opt-in before trying
        to use `set_l` otherwise the user will not have any
        LocalStorage to use and the txn will revert
    """
    @abimethod(allow_actions=["NoOp", "OptIn"], readonly=True)
    def get_version(self) -> UInt64:
        return UInt64(2)

