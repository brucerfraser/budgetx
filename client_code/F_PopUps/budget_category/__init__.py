from ._anvil_designer import budget_categoryTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...F_Global_Logic import BUDGET


class budget_category(budget_categoryTemplate):
  def __init__(self,cat_id, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.item = [c for c in BUDGET.all_sub_cats if c['belongs_to'] == cat_id]
    

  @handle("", "show")
  def form_show(self, **event_args):
    self.repeating_panel_1.items = self.item
    
