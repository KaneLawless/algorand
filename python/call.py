from algosdk import mnemonic, account
from algosdk.v2client import algod
from algosdk.future import transaction

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


m = "!!MNEMONIC!!"
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
client = algod.AlgodClient(algod_token, algod_address)
private_key = get_private_key_from_mnemonic(m)
app_id = "!!APPID!!"
app_args = ["deduct"]

def get_private_key_from_mnemonic(mn):
    private_key = mnemonic.to_private_key(mn)
    return private_key

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
    
call_app(client, private_key, app_id, app_args)