from ._anvil_designer import please_waitTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import time


class please_wait(please_waitTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

  def close_me(self,**event_args):
    self.raise_event('x-close-alert',value=None)

  def form_show(self, **event_args):
    i = 0.1
    self.determinate_1.progress = i
    while True:
      time.sleep(0.1)
      i += 0.05
      self.determinate_1.progress = i
    
