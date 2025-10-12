import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import uuid

global ACCOUNTS
ACCOUNTS = []

accounts = anvil.server.call('get_accounts')
keys = list(accounts.keys())
ACCOUNTS = [(accounts[k],k) for k in keys]

def new_id_needed():
  return str(uuid.uuid4())
