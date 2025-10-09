from ._anvil_designer import Dashboard_ScreenTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...Components.Transactions import Transactions


class Dashboard_Screen(Dashboard_ScreenTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.load_transactions()
    

  def load_transactions(self, **event_args):
    self.link_transactions.add_component(Transactions())

  def link_transactions_click(self, **event_args):
    get_open_form().ping_ping()
    
