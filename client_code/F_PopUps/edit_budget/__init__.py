from ._anvil_designer import edit_budgetTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class edit_budget(edit_budgetTemplate):
  def __init__(self, embedded=True, **properties):
    # Set Form properties and Data Bindings.
    self.embedded=embedded
    self.init_components(**properties)

  @handle("", "show")
  def form_show(self, **event_args):
    if not self.embedded:
      # call edit_switch
      pass
    

