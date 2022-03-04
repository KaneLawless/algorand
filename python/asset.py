import json # For submitting transaction
from pyteal import *
from algosdk.v2client import algod # To connect client to sandbox node
from algosdk.future.transaction import PaymentTxn # To build transaction



# Connect client to sandbox node
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
algod_client = algod.AlgodClient(algod_token, algod_address)


# get network params for txns before every txn
params = algod_client.suggested_params()
# comment below two lines to use suggested params
#params.fee = 1000
#params.flat_fee = True

# Acc 1 creates asset called EmFi and sets Acc2 as manager, reserve, freeze, clawback

# Asset creation txn
txn = AssetConfigTxn(
    sender=accounts[1]['pk'],
    sp=params,
    total=100000000,
    default_frozen=False,
    unit_name="EmFi",
    asset_name="EmFi token",
    manager=accounts[2]["pk"],
    reserve=accounts[2]["pk"],
    freeze=accounts[2]["pk"],
    clawback=accounts[2]["pk"],   
    url="emfi.org",
    decimals=2)

# Sign with private key of creator
stxn = txn.sign(accounts[1]["sk"])

# Send txn to network and retrieve txn id
txid = algod_client.send_transaction(stxn)
print(txid)

# Retrieve the asset ID of the newly created asset by first
# ensuring that the creation transaction was confirmed,
# then grabbing the asset id from the transaction.

# Wait for the transaction to be confirmed
wait_for_confirmation(algod_client,txid)

try:
    # Pull account info for the creator
    # account_info = algod_client.account_info(accounts[1]['pk'])
    # get asset_id from tx
    # Get the new asset's information from the creator account
    ptx = algod_client.pending_transaction_info(txid)
    asset_id = ptx["asset-index"]
    print_created_asset(algod_client, accounts[1]['pk'], asset_id)
    print_asset_holding(algod_client, accounts[1]['pk'], asset_id)
except Exception as e:
    print(e)
