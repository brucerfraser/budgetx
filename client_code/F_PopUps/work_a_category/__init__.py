from ._anvil_designer import work_a_categoryTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.js
import time

class work_a_category(work_a_categoryTemplate):
  def __init__(self, cat=True,**properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.cat = cat
    if not self.cat:
      for thing in [self.flow_panel_1,self.flow_panel_2,self.label_1,self.label_2]:
        thing.visible = False
    self.colorpicker_back.set_color('#C0C9C1')
    self.colorpicker_text.set_color("#000000")
    self.label.text = "Choose name"
    self._update_label()

  def _update_label(self):
    self.label.foreground = self.colorpicker_text.get_color()
    self.label.background = self.colorpicker_back.get_color()

  def colorpicker_text_change(self, **event_args):
    self._update_label()

  def button_1_click(self, **event_args):
    self.raise_event('x-close-alert',value=None)

  def button_2_click(self, **event_args):
    if len(self.label.text) > 2 and not self.label.text.lower() in ["choose name",'income']:
      from ...F_Global_Logic import Global
      id = 'category_id' if self.cat else 'sub_category_id'
      self.raise_event('x-close-alert',value={'name':self.label.text,
                                              'colour_back':self.colorpicker_back.get_color(),
                                             'colour_text':self.colorpicker_text.get_color(),
                                              'roll_over':False,'roll_over_date':None,
                                             id:Global.new_id_needed(),
                                             'order':0})
    else:
      self.button_2.background = 'theme:Error'
      time.sleep(2)
      self.button_2.background = ''

  def colorpicker_back_change(self, **event_args):
    self._update_label()

  def text_box_1_pressed_enter(self, **event_args):
    self.label.text = self.text_box_1.text
    if not self.cat:
      self.button_2_click()

  def text_box_1_update(self, **event_args):
    self.label.text = self.text_box_1.text

  def form_show(self, **event_args):
    self.text_box_1.focus()
    self.text_box_1.select()

    
