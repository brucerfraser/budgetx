from ._anvil_designer import ItemTemplate4Template
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class ItemTemplate4(ItemTemplate4Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)


  def chosen(self,the_one,**event_args):
    if the_one:
      self.link_1.background = 'theme:Secondary'
      self.link_1.foreground = 'blue'
    else:
      self.link_1.background = 'theme:On Background'
      self.link_1.foreground = ''

  @handle("link_1", "click")
  def link_1_click(self, **event_args):
    if self.link_1.foreground != 'blue':
      self.parent.raise_event('x-account-clicked',acc_id=self.item['acc_id'])
    else:
      self.parent.raise_event('x-account-clicked',acc_id='')
