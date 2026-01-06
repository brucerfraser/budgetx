from ._anvil_designer import ReportsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ..Reports_mini import Reports_mini
from ...F_Global_Logic import Global
import anvil.js

LONG_MS = 450

class Reports(ReportsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.column_panel_1.add_component(Reports_mini(full_screen=True))

  @handle("", "show")
  def form_show(self, **event_args):
  # Attach only once per form instance
    pass
