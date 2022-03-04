import json
from pyteal import *
from algosdk.future.transaction import AssetTransferTxn, transaction, PaymentTxn
from algosdk.v2client import algod
from dotenv import load_dotenv
import os



load_dotenv()

# Initialise algod client
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
algod_client = algod.AlgodClient(algod_token,algod_address)

asset_id = ASSETID
students_dict = {
    "s1_addr": "s1_pvt_key",
    "s2_addr":"s2_pvt_key",
    "s3_addr":"s3_pvt_key"}
reserve_address = "CCJTV6PBA54HXHNDGXIVGYPQQVY4GQM27W7I3T2CKUC7EGFZD5GMUTVV7M"
reserve_pvt_key = os.getenv("RESERVE_PVT_KEY")

# Utility function for transaction confirmation or error        
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

# Utility function for retrieving asset balances
def print_asset_holding(algodclient, account, assetid):
    account_info = algodclient.account_info(account)
    for asset in account_info['assets']:
        if (asset['asset-id'] == assetid):
            print("Asset ID: {}".format(asset['asset-id']))
            print(json.dumps(asset, indent=4))
            break


def opt_in(students):
    txns = []
    # Create txn for each student addr and append to txns
    for student in students:
        # Set fee to 0
        params = algod_client.suggested_params()
        params.fee=0
        params.flat_fee=True
        
        # Check if already opted-in
        account_info = algod_client.account_info(student)
        holding = None
        i = 0
        for info in account_info['assets']:
            asset = account_info['assets'][i]
            i += 1
            if asset['asset-id'] == asset_id:
                holding = True
                break
        if not holding:
            # Create opt-in txn
            txn = AssetTransferTxn(
                sender=student,
                sp=params,
                receiver=student,
                amt=0,
                index=asset_id,
            )
            
            txns.append(txn)
            
    #Return list of txns for atomic grouping
    return txns
        
    
def initial_transfer(students):
    txns = []
    
    # Create txn for each student
    # Set fee to 2000 to cover the 0 fees in opt-in txns
    for student in students:   
        params =  algod_client.suggested_params()
        params.fee = 2000
        params.flat_fee = True
        
        txn = AssetTransferTxn(
            sender=reserve_address,
            sp=params,
            receiver=student,
            amt=20000,
            index=asset_id
        )
        
        txns.append(txn)
    # Return txn list for atomic grouping
    return txns

def send_min_bal(students):
    txns = []
    for student in students:
        params =  algod_client.suggested_params()
        params.fee = 1000
        params.flat_fee = True
        
        txn = PaymentTxn(
            sender=reserve_address,
            sp=params,
            amt=200000,
            receiver=student
        )
        
        txns.append(txn)
        
    return txns
        
    
def main():
    opt_in_txns = opt_in(students_dict)
    axfer_txns = initial_transfer(students_dict)
    min_bal_txns = send_min_bal(students_dict)
    
    # Combine txns
    all_txns = min_bal_txns + opt_in_txns + axfer_txns
    # Group txns and assign group id
    stxns = []
    gid = transaction.calculate_group_id(all_txns)
    for txn in all_txns:
        txn.group = gid
        # Sign txns with correct pvt key
        if txn.sender ==  reserve_address:
            stxn = txn.sign(reserve_pvt_key)
            stxns.append(stxn)
        else:
            for student in students_dict:
                if txn.sender ==  student:
                    stxn = txn.sign(students_dict[student])
                    stxns.append(stxn)
                    
    # Send transactions
    tx_id = algod_client.send_transactions(stxns)
    
    # Wait for txn confirmation
    wait_for_confirmation(algod_client, tx_id)
    
    # Print asset balances
    for student in students_dict:
        print_asset_holding(algod_client,student,asset_id)
        
        
main()
    
    
        
        
    
    