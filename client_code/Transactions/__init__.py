from ._anvil_designer import TransactionsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Transactions(TransactionsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    tester = []
    for i in range(0,100):
      tester.append({'name':str(i)})
    self.repeating_panel_1.items = tester
    # Any code you write here will run before the form opens.
