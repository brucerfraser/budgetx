from ._anvil_designer import TesterTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class Tester(TesterTemplate):
  def __init__(self, many_label,rp,**properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    rep = 50
    if many_label:
      for i in range(1,rep):
        self.add_component(Label(text="Hello {n}".format(n=i)))
    if rp:
      l = []
      for i in range(1,rep):
        l.append("Hello rp {n}".format(n=i))
      self.repeating_panel_1.items = l
