from pyteal import *

tmpl_receiver = Addr("VKDOGYU7JOPAD6FKNRD7FETWW4VX7RPEMEZU3NOZPATIABNTVVMRUM3ICY")
tmpl_fee = Int(1000)

def send_if_tx_properties():
    fee_cond = Txn.fee() <= tmpl_fee
    recv_cond = Txn.receiver() == tmpl_receiver

    program = And(fee_cond, recv_cond)

    return program

if __name__ == "__main__":
    print(compileTeal(send_if_tx_properties(), mode=Mode.Signature, version=5))