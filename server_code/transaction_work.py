import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from dateutil.parser import parse
from datetime import date, datetime
import math

@anvil.server.callable
def get_hash_date(date):
  return str(parse(date).day) + str(parse(date).month) + str(parse(date).year)

@anvil.server.callable
def clear_cats():
  for row in app_tables.transactions.search():
    row['category'] = None

@anvil.server.callable
def clean_hash():
  for row in app_tables.transactions.search():
    row['hash'] = str(row['date'].day) + str(row['date'].month) + str(row['date'].year) + str(row['amount']) + row['account']



@anvil.server.callable
def clean_dups():
  quick_trans = []
  for row in app_tables.transactions.search():
    quick_trans.append(dict(row))
  dup_list = []
  for t in quick_trans:
    id = t['transaction_id']
    hash = str(t['date'].day) + str(t['date'].month) + str(t['date'].year) + str(t['amount']) + t['account']
    for tr in quick_trans:
      h = str(tr['date'].day) + str(tr['date'].month) + str(tr['date'].year) + str(tr['amount']) + tr['account']
      if hash == h and tr['transaction_id'] != id:
        # we have a duplicate
        already = False
        for p in dup_list:
          if id in p:
            already = True
            break
        if not already:
          dup_list.append((id,tr['transaction_id']))
          break
  
  for pair in dup_list:
    if app_tables.transactions.get(transaction_id=pair[0])['category']:
      # first of the pairs has been categorised
      app_tables.transactions.get(transaction_id=pair[1]).delete()
    else:
      app_tables.transactions.get(transaction_id=pair[0]).delete()

@anvil.server.callable
def delete_transactions(del_list):
  for transaction in del_list:
    row = app_tables.transactions.get(transaction_id=transaction)
    if row:
      row.delete()
  return True


@anvil.server.callable
def handle_transfers(transfer_list):
  for transfer in transfer_list:
    if transfer['exists']:
      app_tables.transactions.get(transaction_id=transfer['trans_one']).update(transfer_account=transfer['account_two'],
                                                                              category='ec8e0085-8408-43a2-953f-ebba24549d96')
      app_tables.transactions.get(transaction_id=transfer['trans_two']).update(transfer_account=transfer['account_one'],
                                                                              category='ec8e0085-8408-43a2-953f-ebba24549d96')
    else:
      #we have to amend one and make one transaction
      
      f_t = "From" if transfer['amount_two'] > 0 else "To"
      desc = "{f_t} {acc}".format(f_t=f_t,
                                  acc=app_tables.accounts.get(acc_id=transfer['account_one'])['acc_name'])
      hash = transfer['date_two'].strftime("%d%m%Y") + str(transfer['amount_two']) + transfer['account_two']
      app_tables.transactions.add_row(account=transfer['account_two'],
                                     amount=transfer['amount_two'],
                                     transaction_id=transfer['trans_two'],
                                     date=transfer['date_two'],
                                     transfer_account=transfer['account_one'],
                                     category='ec8e0085-8408-43a2-953f-ebba24549d96', #transfers
                                     hash=hash,
                                     description=desc)
      app_tables.transactions.get(transaction_id=transfer['trans_one']).update(transfer_account=transfer['account_two'],
                                                                               category='ec8e0085-8408-43a2-953f-ebba24549d96')