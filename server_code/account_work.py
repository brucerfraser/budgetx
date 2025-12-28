import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

@anvil.server.callable
def get_accounts():
  accounts,a_w = {},[]
  for row in app_tables.accounts.search():
    accounts[row['acc_id']] = row['acc_name']
    a_w.append(dict(row))
  return accounts,a_w

@anvil.server.callable
def update_account(account):
  app_tables.accounts.get(acc_id=account['acc_id']).update(**account)

@anvil.server.callable
def delete_account(account):
  app_tables.accounts.get(acc_id=account['acc_id']).delete()
