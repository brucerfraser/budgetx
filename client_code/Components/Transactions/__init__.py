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
    self.repeating_panel_1.items = app_tables.transactions.search(tables.order_by("date",ascending=False))
    odd = True
    for trans in self.repeating_panel_1.get_components():
      if odd:
        trans.set_bg(True)
      else:
        trans.set_bg(False)
      odd = not odd
    # Any code you write here will run before the form opens.


