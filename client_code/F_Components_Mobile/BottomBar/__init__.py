from ._anvil_designer import BottomBarTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class BottomBar(BottomBarTemplate):
  """
  Properties (for now, simple):
    active_key: str (optional)
  Event:
    x-navigate(key=str)
  """
  def __init__(self, active_key=None, **properties):
    self.init_components(**properties)
    objs = [self.button_1,self.button_2,self.button_3,self.button_4]
    i = 1
    for obj in objs:
      obj.tag = "butt{n}".format(n=i)
      i += 1
    self.active_key = active_key

  def _raise_nav(self, key):
    self.raise_event("x-navigate", key=key)

  @handle('button_1','click')
  @handle('button_2','click')
  @handle('button_3','click')
  @handle('button_4','click')
  def btn_click(self, **event_args):    
    self._raise_nav(event_args['sender'].tag)
  
