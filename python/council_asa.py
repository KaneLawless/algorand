import json
from pyteal import *
from algosdk.future.transaction import AssetConfigTxn # To build transaction
from algosdk.v2client import algod
from dotenv import load_dotenv
import os

load_dotenv()

algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
reserve_address =  "!!RSRV_ADDR!!"
change_address = "!!CHANGE_ADDR!!"
creator_private_key = os.getenv("RESERVE_PVT_KEY")
   
#   Utility function used to print asset holding for account and assetid
def print_asset_holding(algodclient, account, assetid):
    account_info = algodclient.account_info(account)
    for asset in account_info['assets']:
        if (asset['asset-id'] == assetid):
            print("Asset ID: {}".format(asset['asset-id']))
            print(json.dumps(asset, indent=4))
            break
        
        
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

# Initialise algod client
algod_client = algod.AlgodClient(algod_token, algod_address) 

# Get network params before each txn
params = algod_client.suggested_params()
params.fee = 1000
params.flat_fee = True

# Create token with Source account as creator/reserve account
# Change account set to clawback address

# Token creation txn
def create_token():
    txn = AssetConfigTxn(
        sender=reserve_address,
        sp=params,
        total=100000000,
        default_frozen=False,
        unit_name="EmFi",
        asset_name="Emergency Finance Token",
        manager=reserve_address,
        reserve=reserve_address,
        freeze=reserve_address,
        clawback=change_address,
        url="emfi.org",
        decimals=2)

    # Sign txn
    stxn = txn.sign(creator_private_key)

    # Send txn to network and retrieve txid
    txid = algod_client.send_transaction(stxn)
    print("Transaction id: {}".format(txid))

    # Ensure creation transaction was confirmed
    # Retrieve asset ID

    wait_for_confirmation(algod_client, txid)

    try:
        # Pull acc info for creator
        # Account info = algod_client.account_info(creator_address)
        # Get asset ID from tx
        # Get new asset info from creator account
        ptx = algod_client.pending_transaction_info(txid)
        asset_id = ptx["asset-index"]
        print_asset_holding(algod_client, reserve_address, asset_id)
    except Exception as e:
        print(e)
        

create_token()

