def create_app(client, private_key, approval_program, clear_program, global_schema, local_schema):
    # Define sender as creator
    sender = account.address_from_private_key(private_key)
    
    # Declare OnComplete as NoOp
    on_complete = transaction.OnComplete.NoOpOC.real
    
    # Get sugg params
    params = client.suggested_params()
    
    # Create utxn
    txn = transaction.ApplicationCreateTxn(sender, params, on_complete, \
                                            approval_program, clear_program, \
                                            global_schema, local_schema)
    
    # Sign txn
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()
    
    # Send txn
    client.send_transactions([signed_txn])
    
    # Wait for confirmation
    wait_for_confirmation(client, tx_id, 5)
    
    # Display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response['application_index']
    print('params used: ', params)
    print('Created new app-id: ', app_id)
    
    return app_id