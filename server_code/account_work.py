import anvil.files
from anvil.files import data_files
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server

@anvil.server.callable
def get_accounts():
  accounts = {}
  for row in app_tables.accounts.search():
    accounts[row['acc_id']] = row['acc_name']
  return accounts
