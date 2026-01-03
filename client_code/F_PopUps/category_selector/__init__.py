from ._anvil_designer import category_selectorTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ...F_Global_Logic import Global


class category_selector(category_selectorTemplate):
  def __init__(self, lbl,cat=None,**properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.cats = [item['display'] for item in Global.CATEGORIES.values()]
    self.rp_options.set_event_handler('x-close-up-shop',self.return_value)
    self.lbl_description.text = lbl
    self.cat = cat if cat else None
  
  @handle("", "show")
  def form_show(self, **event_args):
    if self.cat:
      self.txt_entry.text = self.cat
      self.ping_ping()
      self.txt_entry.select()
    else:
      self.txt_entry.focus()
    

  @handle('txt_entry','pressed_enter')
  def select_top(self,**event_args):
    if len(self.rp_options.get_components()) > 0:
      c = self.rp_options.get_components()[0].item
      self.return_value(cat=c)
    else:
      self.raise_event('x-close-alert',value="")

  @handle('txt_entry','change')
  def ping_ping(self,**event_args):
    if self.txt_entry.text:
      self.rp_options.visible = True
      t = self.txt_entry.text
      self.rp_options.items = [l for l in self.cats if t.lower() in l.lower()]
    else:
      self.rp_options.visible = False
      self.rp_options.items = []

  def return_value(self,cat,**event_args):
    self.raise_event('x-close-alert',value=cat)

    
