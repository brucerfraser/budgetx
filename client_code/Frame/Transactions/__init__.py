from ._anvil_designer import TransactionsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ... import Global


class Transactions(TransactionsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.accounts = anvil.server.call('get_accounts')
    keys = list(self.accounts.keys())
    self.dd_list = [(self.accounts[k],k) for k in keys]
    # self.repeating_panel_1.accounts = [(self.accounts[k],k) for k in keys]
    # self.repeating_panel_1.add_event_handler('x-get-accounts',self.get_account_list)
    self.repeating_panel_1.items = app_tables.transactions.search()
    # Any code you write here will run before the form opens.

  def get_account_list(self,**event_args):
    keys = list(self.accounts.keys())
    return [(self.accounts[k],k) for k in keys]
