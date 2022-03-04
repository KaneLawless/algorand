import base64

from algosdk.future import transaction
from algosdk import account, mnemonic
from algosdk.v2client import algod 
from pyteal import *


creator_mnemonic = ""
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


# Helper function to compile program source
def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])

def get_private_key_from_mnemonic(mn):
    private_key = mnemonic.to_private_key(mn)
    return private_key

def wait_for_confirmation(client, txn_id, timeout):
    # Wait until the transaction is confirmed or rejected, or until 'timeout'
    # number of rounds have passed.
    # Args:
    #     transaction_id (str): the transaction to wait for
    #     timeout (int): maximum number of rounds to wait
    # Returns:
    #     dict: pending transaction information, or throws an error if the transaction
    #         is not confirmed or rejected in the next timeout rounds
    
    start_round = client.status()["last-round"] + 1
    current_round = start_round
    while current_round < start_round + timeout:
        try:
            pending_txn = client.pending_transaction_info(txn_id)
        except Exception:
            return
        if pending_txn.get("confirmed-round", 0) > 0:
            return pending_txn
        elif pending_txn["pool-error"]:
            raise Exception(
                "pool error: {}".format(pending_txn["pool-error"]))
        client.status_after_block(current_round)
        current_round += 1
        
    raise Exception(
        "pending txn not found in timeout rounds, timeout value = {}".format(timeout))
        
            
# Helper function to format global state for printing
def format_state(state):
    formatted = {}
    for item in state:
        key = item["key"]
        value = item["value"]
        formatted_key = base64.b64decode(key).decode("utf-8")
        if value["type"] == 1:
            # byte string
            if formatted_key == 'voted':
                formatted_value = base64.b64decode(value['bytes']).decode("utf-8")
            else:
                formatted_value = value['bytes']
            formatted[formatted_key] = formatted_value
        else:
            # integer
            formatted[formatted_key] = value["uint"]
    return formatted

# Helper function to read global state
def read_global_state(client, app_id):
    app = client.application_info(app_id)
    global_state = app['params']['global-state'] if 'global-state' in app['params'] else []
    return format_state(global_state)

def approval_program():
    
    handle_creation = Seq(
        App.globalPut(Bytes("Count"), Int(0)),
        Return(Int(1))
    )
    
    scratchCount = ScratchVar(TealType.uint64)
    
    add = Seq(
        # Store Count value in scratch space
        scratchCount.store(App.globalGet(Bytes("Count"))),
        App.globalPut(Bytes("Count"), scratchCount.load() + Int(1)),
        Return(Int(1))
    )
    
    deduct = Seq(
        scratchCount.store(App.globalGet(Bytes("Count"))),
        # Ensure count doesn't become negative
        If(scratchCount.load() > Int(0),
           App.globalPut(Bytes("Count"), scratchCount.load() - Int(1)),
        ),
        Return(Int(1))
        
    )
    
    handle_noop = Seq(
        # Fail if txn is grouped
        Assert(Global.group_size() == Int(1)),
        Cond(
            [Txn.application_args[0] == Bytes("add"), add],
            [Txn.application_args[0] == Bytes("deduct"), deduct]   
        )
    )
    
    handle_optin = Return(Int(0))
    handle_closeout = Return(Int(0))
    handle_update = Return(Int(0))
    handle_delete = Return(Int(0))
    program = Cond(
        [Txn.application_id() == Int(0), handle_creation],
        [Txn.on_completion() == OnComplete.OptIn, handle_optin],
        [Txn.on_completion() == OnComplete.CloseOut, handle_closeout],
        [Txn.on_completion() == OnComplete.UpdateApplication, handle_update],
        [Txn.on_completion() == OnComplete.DeleteApplication, handle_delete],
        [Txn.on_completion() == OnComplete.NoOp, handle_noop]
    )
    
    return compileTeal(program, Mode.Application, version=5)

def clear_state_program():
    program = Return(Int(1))
    
    return compileTeal(program, Mode.Application, version=5)

def create_app(client, private_key, approval_program, clear_program, global_schema, local_schema):
    # Define sender as creator
    sender = account.address_from_private_key(private_key)
    
    # Declare OnComplete as NoOp
    on_complete = transaction.OnComplete.NoOpOC.real
    
    # Get sugg params
    params = client.suggested_params()
    
    # Create utxn
    txn = transaction.ApplicationCreateTxn(sender, params, on_complete, \
                                            approval_program, clear_program, \
                                            global_schema, local_schema)
    
    # Sign txn
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()
    
    # Send txn
    client.send_transactions([signed_txn])
    
    # Wait for confirmation
    wait_for_confirmation(client, tx_id, 5)
    
    # Display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response['application-index']
    print('Created new app-id: ', app_id)
    
    return app_id

def call_app(client, private_key, index, app_args):
    # declare sender
    sender = account.address_from_private_key(private_key)
    
    # get node sugg params
    params = client.suggested_params()

    # create utxn
    txn = transaction.ApplicationNoOpTxn(sender, params, index, app_args)
    
    # sign txn
    stxn = txn.sign(private_key)
    tx_id = stxn.transaction.get_txid()
    
    # send txn
    client.send_transactions([stxn])
    
    # await confirmation
    wait_for_confirmation(client, tx_id, 5)
    
    print("Application called")
    
def main() :
    # initialize algod client
    algod_client = algod.AlgodClient(algod_token, algod_address)
    
    # define private keys
    creator_private_key = get_private_key_from_mnemonic(creator_mnemonic)
    
    # define application state storage (immutable)
    local_ints = 0
    local_bytes = 0
    global_ints = 1
    global_bytes = 0
    global_schema = transaction.StateSchema(global_ints, global_bytes)
    local_schema = transaction.StateSchema(local_ints, local_bytes)
    
    # compile program to TEAL assembly
    with open("./teal/approval.teal", 'w') as f:
        approval_program_teal = approval_program()
        f.write(approval_program_teal)
        
    # compile program to TEAL assembly
    
    with open("./teal/clear.teal", 'w') as f:
        clear_state_program_teal = clear_state_program()
        f.write(clear_state_program_teal)
        
    # compile progam to binary
    approval_program_compiled = compile_program(algod_client, approval_program_teal)
    
    # compile program to binary
    clear_state_program_compiled = compile_program(algod_client, clear_state_program_teal)
    
    print("-------------------------------------------------")
    print("Deploying counter application")
    
    # create new application
    app_id = create_app(algod_client, creator_private_key, approval_program_compiled, clear_state_program_compiled, global_schema, local_schema)
    
    print("Global state:", read_global_state(algod_client, app_id))


    print("--------------------------------------------------")
    print("Calling counter application........")
    app_args = ["deduct"]
    call_app(algod_client, creator_private_key, app_id, app_args)
    
    
    # read global state
    print("Global state:", read_global_state(algod_client, app_id))
    

main()
