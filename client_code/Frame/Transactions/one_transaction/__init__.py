from ._anvil_designer import one_transactionTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class one_transaction(one_transactionTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    
    self.accounts = self.parent.accounts
    self.init_components(**properties)
    # self.accounts = self.parent.raise_event('x-get-accounts')
    # self.drop_down_1.items = self.accounts
    self.date.tag = 'date'
    
    # Any code you write here will run before the form opens.

  def click_date(self, **event_args):
    self.date_picker_1.visible = True
    self.date_picker_1.focus()
    self.date.visible = False

  def date_picker_1_change(self, **event_args):
    self.parent.items = app_tables.transactions.search()
    self.date_picker_1.visible = False
    self.date.visible = True

  def click_account(self, **event_args):
    self.drop_down_1.visible = True
    self.drop_down_1.focus()
    self.account.visible = False

  
