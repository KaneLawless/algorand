from pyteal import *

"""Basic Counter Smart Contract """

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

print(approval_program())
print(clear_state_program())