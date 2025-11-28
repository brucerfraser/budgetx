from ._anvil_designer import ItemTemplate1Template
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class ItemTemplate1(ItemTemplate1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    if self.item['date'] == 'Transaction Date':
      self.make_header()
    self.border = '1px solid grey'
    try:
      self.amount.text = self.item['amount'] / 100
    except:
      pass
    
    # Any code you write here will run before the form opens.

  def make_header(self,**args):
    for object in self.get_components():
      object.bold = True
      object.underline = True
      object.font_size = 18

  