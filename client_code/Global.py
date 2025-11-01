import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import uuid
from datetime import date

global ACCOUNTS
ACCOUNTS = []

global PERIOD
PERIOD = (0,0)

accounts = anvil.server.call('get_accounts')
keys = list(accounts.keys())
ACCOUNTS = [(accounts[k],k) for k in keys]

def new_id_needed():
  return str(uuid.uuid4())

def make_date(m=None,y=None):
  global PERIOD
  if m:
    pass
  else:
    t = date.today()
    PERIOD = (t.month-2,t.year)


