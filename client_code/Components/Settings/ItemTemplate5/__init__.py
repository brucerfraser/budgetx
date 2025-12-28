from ._anvil_designer import ItemTemplate5Template
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class ItemTemplate5(ItemTemplate5Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.to_delete = False

  # @handle("", "show")
  # def form_show(self, **event_args):
  #   self.text_box_1.text = self.item

  @handle('text_box_1','change')
  def change_me(self,**event_args):
    self.parent.raise_event('x-changed',caller='auto')

  @handle('text_box_1','pressed_enter')
  def add_me(self,**event_args):
    self.parent.raise_event('x-pressed-enter',key_word=self.text_box_1.text)

  @handle('btn_del_key','click')
  def delete_me(self,**event_args):
    self.to_delete = True
    self.parent.raise_event('x-delete-key')
    
    
  
