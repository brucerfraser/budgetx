from ._anvil_designer import ReportsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ... import Global
from ..Reports_mini import Reports_mini


class Reports(ReportsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.cp_reports.add_component(Reports_mini(full_screen=True))
  

 