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
    buttons: list of dicts tells bar which buttons to show (invis if not incl), text, role, icons,text colour
    {'text':'','role':'','icon':'','future':'','colour':''}
  Event:
    x-navigate(key=str)
  """
  def __init__(self, buttons=None, **properties):
    
    
    self.init_components(**properties)
    objs = [self.button_1,self.button_2,self.button_3,self.button_4,self.button_5]
    i = 1
    for obj in objs:
      obj.tag = "butt{n}".format(n=i)
      i += 1
    self.update_buttons(buttons)

  def _raise_nav(self, key):
    self.raise_event("x-navigate", key=key)

  @handle('button_1','click')
  @handle('button_2','click')
  @handle('button_3','click')
  @handle('button_4','click')
  @handle('button_5','click')
  def btn_click(self, **event_args):    
    self._raise_nav(event_args['sender'].tag)

  def update_buttons(self,buttons,**event_args):
    objs = [self.button_1,self.button_2,self.button_3,self.button_4,self.button_5]
    i = 0
    
    if buttons:
      for button in buttons:
        objs[i].text = button['text']
        objs[i].role = button['role']
        objs[i].icon = button['icon']
        objs[i].foreground = button['colour']
        objs[i].enabled = button['enabled']
        objs[i].visible = True
        i += 1
      if i < len(objs):
        for v in range(i,len(objs)):
          objs[v].visible = False
    else:
      for obj in objs:
        obj.visible = False
  
