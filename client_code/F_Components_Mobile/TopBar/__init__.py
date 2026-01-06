from ._anvil_designer import TopBarTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables


class TopBar(TopBarTemplate):
  """
  Properties (for now, simple):
    label: dict tells bar how to format label_1, text, role, icons,text colour
    {'text':'','role':'','icon':'','future':'','colour':''}
  Event:
    x-navigate(key=str)
  """

  def __init__(self, label=None, **properties):
    self.init_components(**properties)
    if label:
      self.update_label(label)

  def _raise_nav(self, key):
    self.raise_event("x-navigate", key=key)

  

  def update_label(self, label, **event_args):
    self.label_1.role = label['role']
    self.label_1.text = label['text']
    self.label_1.foreground = label['colour']
    self.label_1.icon = label['icon']

    