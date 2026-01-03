import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import Global

def work_transaction_data(mode,transaction):
  if mode == 'add':
    Global.TRANSACTIONS.insert(0,transaction)
    app_tables.transactions.add_row(**transaction)
    Global.Transactions_Form.load_me()
    
