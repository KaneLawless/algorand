import base64
from pyteal import *
from algosdk.future import transaction
from algosdk.future.transaction import PaymentTxn
from algosdk import account, logic
from algosdk.v2client import algod
from dotenv import load_dotenv
import os

load_dotenv()
manager_pvt_key = os.getenv("RESERVE_PVT_KEY")
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
asset_id = int(os.getenv("EMFI_ASSET_ID"))
council_redeem_addr = ""


def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])    
    
def wait_for_confirmation(client, txid):
    last_round = client.status().get('last-round')
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round')> 0):
        print("Waiting for confirmation")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    print("Transaction {} confirmed in round {}".format(txid, txinfo.get('confirmed-round')))
    return txinfo
        
        
def approval_program(asset_id, council_redeem):
    
    scratchAmount = ScratchVar(TealType.uint64)
    scratchCount = ScratchVar(TealType.uint64)
    scratchTotal = ScratchVar(TealType.uint64)
    isAppOptin = AssetHolding.balance(Global.current_application_address(), Int(0))
    
    
    standardNoop = Seq(
        Assert(Global.group_size() == Int(2)),
        Assert(Gtxn[0].sender() == Gtxn[1].sender()),
        Assert(Gtxn[1].type_enum() == TxnType.AssetTransfer),
        Assert(Gtxn[1].xfer_asset() == Int(asset_id)),
        Assert(Gtxn[1].asset_receiver() == Global.current_application_address()),
        
        scratchAmount.store(Gtxn[1].asset_amount()),
        scratchCount.store(App.localGet(Txn.sender(), Bytes("transaction_count"))),
        scratchTotal.store(App.localGet(Txn.sender(), Bytes("total_redeemed"))),
        Assert(scratchAmount.load() <= Gtxn[1].asset_amount()),
        
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_amount: scratchAmount.load(),
            TxnField.asset_receiver: Addr(council_redeem),
            TxnField.xfer_asset: Int(asset_id), #  Must be in assets array
        }),
        InnerTxnBuilder.Submit(),
            
        App.localPut(Txn.sender(), Bytes("total_redeemed"), scratchTotal.load() + scratchAmount.load()),
        App.localPut(Txn.sender(), Bytes("transaction_count"), scratchCount.load() + Int(1)),
        Return(Int(1)),
        )
    
    
    optinToAsset = Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            TxnField.asset_amount: Int(0),
            TxnField.asset_receiver: Global.current_application_address(),
            TxnField.fee: Int(1000),
            TxnField.xfer_asset: Int(asset_id),
        }),
        InnerTxnBuilder.Submit(),
        Return(Int(1)),
    )
    
    
    handle_optin = Seq(
        # Check if already opted in
        If(App.optedIn(Int(0), Txn.application_id()),
           Return(Int(1)),
        ),
        Assert(Global.group_size() == Int(1)),
        Assert(Txn.asset_amount() == Int(0)),
        Return(Int(1))
    )
    
    
    handle_noop = Seq(
        isAppOptin,
        Cond(
        [isAppOptin.hasValue() == Int(1), standardNoop],
        [isAppOptin.hasValue() == Int(0), optinToAsset]
        )
    )

        
    handle_creation = Return(Int(1))
    handle_update = Return(Int(0))
    handle_closeout = Return(Int(0))
    handle_delete = Return(Int(0))
    
    
    program = Cond(
        [Txn.application_id() == Int(0), handle_creation],
        [Txn.on_completion() == OnComplete.OptIn, handle_optin],
        [Txn.on_completion() == OnComplete.UpdateApplication, handle_update],
        [Txn.on_completion() == OnComplete.DeleteApplication, handle_delete],
        [Txn.on_completion() == OnComplete.CloseOut, handle_closeout],
        [Txn.on_completion() == OnComplete.NoOp, handle_noop]
    )
    
    return compileTeal(program, Mode.Application, version=5)

def clear_state_program():
    program = Return(Int(1))
    
    return compileTeal(program, Mode.Application, version=5)


def create_app(client,private_key,approval_program,clear_program,global_schema,local_schema, foreign_assets):
    
    sender = account.address_from_private_key(private_key)
    
    on_complete = transaction.OnComplete.NoOpOC.real
    
    params = client.suggested_params()
    params.fee = 2000
    
    txn = transaction.ApplicationCreateTxn(sender,params,on_complete, approval_program,clear_program,global_schema,local_schema,foreign_assets=foreign_assets)
    
    stxn = txn.sign(private_key)
    txid = stxn.transaction.get_txid()
    
    client.send_transactions([stxn])
    
    wait_for_confirmation(client,txid)
    
    transaction_response = client.pending_transaction_info(txid)
    
    app_id = transaction_response["application-index"]
    print("Created new application id: {}".format(app_id))
        
    return app_id


def get_app_addr(app_id):
    addr = logic.get_application_address(app_id)
    return addr


def initial_algo_xfer(client, private_key, app_addr):
    
    sender = account.address_from_private_key(private_key)
    params = client.suggested_params()
    txn = PaymentTxn(sender,params,app_addr,1000000)
    
    stxn = txn.sign(private_key)
    txid = client.send_transactions([stxn])
    wait_for_confirmation(client, txid)
    
    
def main():
    
    algod_client = algod.AlgodClient(algod_token,algod_address)
    
    creator_pvt_key = manager_pvt_key
    assetid = asset_id
    councilRedeem = council_redeem_addr
    foreign_assets = [asset_id]
    
    local_ints = 2
    local_bytes = 0
    global_ints = 0
    global_bytes = 0
    global_schema = transaction.StateSchema(global_ints,global_bytes)
    local_schema = transaction.StateSchema(local_ints, local_bytes)
    
    with open("./teal/redeem2Approval.teal", "w") as f:
        approval_program_teal = approval_program(assetid, councilRedeem)
        f.write(approval_program_teal)
        
    with open("./teal/redeem2csp.teal", "w") as f:
        clear_state_program_teal = clear_state_program()
        f.write(clear_state_program_teal)
        
    approval_program_compiled = compile_program(algod_client, approval_program_teal)
    clear_state_program_compiled = compile_program(algod_client, clear_state_program_teal)
    
    app_id = create_app(algod_client, creator_pvt_key,approval_program_compiled,clear_state_program_compiled,
               global_schema,local_schema, foreign_assets)
    
    app_addr = get_app_addr(app_id)
    print("Application Escrow Address: " + app_addr)
    
    initial_algo_xfer(algod_client, creator_pvt_key, app_addr)
    

main()