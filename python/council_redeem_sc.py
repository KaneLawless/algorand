import base64
from pyteal import *
from algosdk.future import transaction
from algosdk.v2client import algod
from algosdk import account
from dotenv import load_dotenv
import os

load_dotenv()

algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
asset_id = ""
reserve_address = ""
reserve_pvt_key = os.getenv("RESERVE_PVT_KEY")


# Helper function to compile program source
def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])


# Utility function to provide transaction confirmation information
def wait_for_confirmation(client, txid):
    """
    Utility function to wait until the transaction is
    confirmed before proceeding.
    """
    last_round = client.status().get('last-round')
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
        print("Waiting for confirmation")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    print("Transaction {} confirmed in round {}.".format(txid, txinfo.get('confirmed-round')))
    return txinfo


# SC approval program 
def approval_program():
    
    handle_optin =  Seq(
        # Check if account already opted in
        If(App.optedIn(Int(0),Txn.application_id()),
           Return(Int(1))
           ),
        Return(Int(1))
    )
    
    # Initialise scratch variables
    scratchTotal = ScratchVar(TealType.uint64)
    scratchCount = ScratchVar(TealType.uint64)
    scratchValue = ScratchVar(TealType.uint64)
    
    handle_noop = Seq(
        
        # Assert txn groupsize==2, Axfer txn is asset transfer, sender is the same for both txns,
        # Receiver is the council redeem address, asset is our asset.
        Assert(Global.group_size() ==  Int(2)),
        Assert(Gtxn[1].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[1].sender() == Gtxn[0].sender()),
        Assert(Gtxn[1].asset_receiver() == Addr("REDEEM_ADDR")),
        Assert(Gtxn[1].xfer_asset() == Int(asset_id)),
        
        # Read asset transfer value from transaction
        # and previous local value for total_redeemed and number of previous transactions
        # Store values in scratch space
        scratchValue.store(Gtxn[1].asset_amount()),
        scratchTotal.store(App.localGet(Txn.sender(),Bytes("total_redeemed"))),
        scratchCount.store(App.localGet(Txn.sender(), Bytes("transaction_count"))),
        
        # Write to local storage to updated total tokens redeemed and txn count
        App.localPut(Txn.sender(), Bytes("total_redeemed"), scratchTotal.load() + scratchValue.load()),
        App.localPut(Txn.sender(), Bytes("transaction_count"), scratchCount.load() + Int(1)),
        Return(Int(1))
    )
    
    handle_creation = Return(Int(1))
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
    wait_for_confirmation(client, tx_id)
    
    # Display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response['application-index']
    print('Created new app-id: ', app_id)
    
    return app_id


def main():
    algod_client = algod.AlgodClient(algod_token,algod_address)
    
    creator_pvt_key = reserve_pvt_key
    
    local_ints = 2
    local_bytes = 0
    global_ints = 0
    global_bytes = 0
    global_schema = transaction.StateSchema(global_ints, global_bytes)
    local_schema = transaction.StateSchema(local_ints, local_bytes)
    
    with open("./teal/redeemApproval.teal", 'w') as f:
        approval_program_teal = approval_program()
        f.write(approval_program_teal)
            
    with open("./teal/redeemClear.teal", "w") as f:
        clear_program_teal = clear_state_program()
        f.write(clear_program_teal)
    
    # compile progam to binary
    approval_program_compiled = compile_program(algod_client, approval_program_teal)
    
    # compile program to binary
    clear_program_compiled = compile_program(algod_client, clear_program_teal)
    
    create_app(algod_client,creator_pvt_key,approval_program_compiled,clear_program_compiled,global_schema,local_schema)
    
    
main()