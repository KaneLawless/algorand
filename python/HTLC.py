from algosdk import algod, transaction, template
# Create an algod client
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
algod_address = "http://localhost:4001"
client = algod.AlgodClient(algod_token, algod_address)
# Get suggested parameters from the network
tx_params = client.suggested_params()
# Specify TLHC-related template params.
template_data = {
    "owner": "FMKZXXC2DW7ULW7JAUKNOLEEK43PMMGSORV6ZV3OGMFHBJ36KYPHJUM4GM",
    "receiver": "VKDOGYU7JOPAD6FKNRD7FETWW4VX7RPEMEZU3NOZPATIABNTVVMRUM3ICY",
    "hash_function": "sha256",
    "hash_image": "QzYhq9JlYbn2QdOMrhyxVlNtNjeyvyJc/I8d8VAGfGc=",
    "expiry_round": 5000000,
    "max_fee": 2000
}
## Inject template data into HTLC template
c = template.HTLC(**template_data)
# Get the address for the escrow account associated with the logic
addr = c.get_address()
print("Escrow Address: {}\n".format(addr))

# Retrieve the program bytes
program = c.get_program()
# Get the program and parameters and use them to create an lsig
# For the contract account to be used in a transaction
# In this example 'hero wisdom green split loop element vote belt'
# hashed with sha256 will produce our image hash
# This is the passcode for the HTLC 
args = [
    "hero wisdom green split loop element vote belt".encode()
]
# Add the program bytes and args to a LogicSig object 
lsig = transaction.LogicSig(program, args)


# Create transaction
tx_data = {
    "sender": addr,
    "receiver": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ",
    "amt": 0,
    "close_remainder_to": "VKDOGYU7JOPAD6FKNRD7FETWW4VX7RPEMEZU3NOZPATIABNTVVMRUM3ICY",
    "fee": 1000,
    "flat_fee": True,
    "first": tx_params.get('lastRound'),
    "last": tx_params.get('lastRound') + 1000,
    "gen": tx_params.get('genesisID'),
    "gh": tx_params.get('genesishashb64')
}
# Instantiate a payment transaction type
txn = transaction.PaymentTxn(**tx_data)
# Instantiate a LogicSigTransaction with the payment txn and the logicsig
logicsig_txn = transaction.LogicSigTransaction(txn, lsig)

# Send the transaction to the network.
txid = client.send_transaction(logicsig_txn, headers={'content-type': 'application/x-binary'})
print("Transaction ID: {}".format(txid))

