def main() :
    # initialize algod client
    algod_client = algod.AlgodClient(algod_token, algod_address)
    
    # define private keys
    creator_private_key = get_private_key_from_mnemonic(creator_mnemonic)
    
    # define application state storage (immutable)
    local_ints = 0
    local_bytes = 0
    global_ints = 1
    global_bytes = 0
    global_schema = transaction.StateSchema(global_ints, global_bytes)
    local_schema = transaction.StateSchema(local_ints, local_bytes)
    
    # compile program to TEAL assembly
    with open("./teal/approval.teal", 'w') as f:
        approval_program_teal = approval_program()
        f.write(approval_program_teal)
        
    # compile program to TEAL assembly
    
    with open("./teal/clear.teal", 'w') as f:
        clear_state_program_teal = clear_state_program()
        f.write(clear_state_program_teal)
        
    # compile progam to binary
    approval_program_compiled = compile_program(algod_client, approval_program_teal)
    
    # compile program to binary
    clear_state_program_compiled = compile_program(algod_client, clear_state_program_teal)
    
    print("-------------------------------------------------")
    print("Deploying counter application")
    
    # create new application
    app_id = create_app(algod_client, creator_private_key, approval_program_compiled, clear_state_program_compiled, global_schema, local_schema)
    
    print("--------------------------------------------------")
    print("Calling counter application........")
    app_args = ["Add"]
    call_app(algod_client, creator_private_key, app_id, app_args)
    
    
    # read global state
    print("Global state:", read_global_state(algod_client, app_id))
    