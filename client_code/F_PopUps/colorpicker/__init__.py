from ._anvil_designer import colorpickerTemplate
from anvil import *
import anvil

class colorpicker(colorpickerTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    dom_node = anvil.js.get_dom_node(self)
    self.color_node = dom_node.querySelector("input")
    self.color_node.onchange = self.color_changed

  def color_changed(self, js_event):    
    self.raise_event('change', color=self.color_node.value)

  def set_color(self, col_hex):
    self.color_node.value = col_hex

  def get_color(self) -> str:
    return self.color_node.value