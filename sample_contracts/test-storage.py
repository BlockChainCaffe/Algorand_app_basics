from    collections.abc import Generator
import  algopy
import  pytest
from    algopy_testing import AlgopyTestContext, algopy_testing_context
from    algokit_utils import CommonAppCallParams, SendParams

# Import contract

from storage import Storage

#------------------------------------------------------------------------------
## Create context with fixture
@pytest.fixture()
def context() -> Generator[AlgopyTestContext, None, None]:
    with algopy_testing_context() as ctx:
        yield ctx

@pytest.fixture()
def contract() -> Storage:
    contract = Storage()
    return contract

#------------------------------------------------------------------------------
## Basic test Tests
def test_get_version(context: AlgopyTestContext, contract:Storage) -> None:
    version = contract.get_version()
    assert version == 2, "Wrong version should be 2"


def test_global(context: AlgopyTestContext, contract:Storage) -> None:
    val = context.any.uint64()
    contract.set_g(val)

    read = contract.get_g()
    assert read == val, "Failed global test"


"""
    Can't test opt-in using the contract object from algopy-test !!!
    
"""
def test_optin(context: AlgopyTestContext, contract:Storage) -> None:
    ## create complete call params
    app_call_params={
        # 'args' : (),
        'params' : CommonAppCallParams(
            on_complete=1,
        ),
        # From algokit-utils >= 4.0.0 the followin line will not be necessary
        'send_params' : SendParams(populate_app_call_resources=True),
    }
    A = contract.get_version().
    
    (
        params = CommonAppCallParams(on_complete=1),
        send_params = SendParams(populate_app_call_resources=True)
    )
    pass


## Advanced test with parametrization
# @pytest.mark.parametrize( ("a", "b"),
#     [
#         (1, b""),
#         (13, b""),
#         (0, b""),
#         (234234, b"box_map"),
#     ],
# )
# def test_another_method(
#     context: AlgopyTestContext,
#     contract: Storage,
#     a: algopy.UInt64,
#     b: bytes
# ) -> None:
#     ## Arrange
#     ## Act
#     ## Assert
#     pass


#------------------------------------------------------------------------------
## Clear state program
@pytest.mark.usefixtures("context")
def test_clear_state_program() -> None:
    contract = Storage()
    assert contract.clear_state_program()