from algosdk import account, mnemonic # To generate account

def generate_algorand_keypair():
    private_key, address = account.generate_account()
    print("Address: {}".format(address))
    print("Private key: {}".format(private_key))
    print("Passphrase: {}".format(mnemonic.from_private_key(private_key)))
    
generate_algorand_keypair()
generate_algorand_keypair()
generate_algorand_keypair()